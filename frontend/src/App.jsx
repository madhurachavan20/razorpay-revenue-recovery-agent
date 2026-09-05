import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import "./App.css";
import Login from "./Login";
import {
  getDashboardSummary,
  getRecoveryOpportunities,
  getPayments,
  getCustomers,
  getAnalyticsOverview,
  getPaymentMethodAnalytics,
  getFailureCategoryAnalytics,
  getRecoveryDetails,
  executeRecovery,
  getRecoveryHistory,
  resetRecovery,
} from "./services/api";

const P = ["HIGH", "MEDIUM", "LOW"];

const NAV = [
  ["Overview", "⌂"],
  ["Recovery", "↻"],
  ["Payments", "▣"],
  ["Customers", "♙"],
  ["Analytics", "⌁"],
];

const EMPTY = {
  payment_metrics: {
    total_transactions: 0,
    successful_payments: 0,
    failed_payments: 0,
    success_rate: 0,
    failure_rate: 0,
    total_transaction_value: 0,
  },

  recovery_metrics: {
    total_failed_payments: 0,
    revenue_at_risk: 0,
    expected_recovery: 0,
    recovery_rate: 0,
    average_recovery_probability: 0,
  },

  priority_distribution: {
    HIGH: 0,
    MEDIUM: 0,
    LOW: 0,
  },

  payment_method_breakdown: [],
  failure_category_breakdown: [],
  top_opportunities: [],
};

const n = (x) => Number(x || 0);

const money = (x) =>
  `₹${n(x).toLocaleString("en-IN", {
    maximumFractionDigits: 0,
  })}`;

const num = (x) =>
  n(x).toLocaleString("en-IN");

const pct = (x) =>
  `${(n(x) * 100).toFixed(2)}%`;

const nice = (x) =>
  String(x || "UNKNOWN")
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());

function normalize(x) {
  return {
    ...EMPTY,
    ...x,

    payment_metrics: {
      ...EMPTY.payment_metrics,
      ...x?.payment_metrics,
    },

    recovery_metrics: {
      ...EMPTY.recovery_metrics,
      ...x?.recovery_metrics,
    },

    priority_distribution: {
      HIGH: n(x?.priority_distribution?.HIGH),
      MEDIUM: n(x?.priority_distribution?.MEDIUM),
      LOW: n(x?.priority_distribution?.LOW),
    },

    payment_method_breakdown:
      Array.isArray(x?.payment_method_breakdown)
        ? x.payment_method_breakdown
        : [],

    failure_category_breakdown:
      Array.isArray(x?.failure_category_breakdown)
        ? x.failure_category_breakdown
        : [],

    top_opportunities:
      Array.isArray(x?.top_opportunities)
        ? x.top_opportunities
        : [],
  };
}

/* =========================================================
   HEADER
========================================================= */

function Header({ eyebrow, title, tag }) {
  return (
    <div className="cardHead">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h2>{title}</h2>
      </div>

      {tag && <span className="tag">{tag}</span>}
    </div>
  );
}

/* =========================================================
   METRIC
========================================================= */

function Metric({
  icon,
  title,
  value,
  sub,
  tone = "",
}) {
  return (
    <div className="metric">
      <div className={`metricIcon ${tone}`}>
        {icon}
      </div>

      <div>
        <span>{title}</span>
        <strong>{value}</strong>
        <small>{sub}</small>
      </div>
    </div>
  );
}

/* =========================================================
   BADGE
========================================================= */

function Badge({ p }) {
  return (
    <span
      className={`badge ${String(
        p || "LOW"
      ).toLowerCase()}`}
    >
      {p || "LOW"}
    </span>
  );
}

/* =========================================================
   BARS
========================================================= */

function Bars({
  items,
  name,
  count,
  moneyKey,
  moneyLabel,
}) {
  if (!items.length) {
    return (
      <div className="empty">
        No analytics data available.
      </div>
    );
  }

  const max = Math.max(
    ...items.map((x) => n(x[count])),
    1
  );

  return (
    <div className="bars">
      {items.slice(0, 7).map((x, i) => (
        <div
          className="barItem"
          key={`${String(x[name])}-${i}`}
        >
          <div className="barLabel">
            <b>{nice(x[name])}</b>
            <span>{num(x[count])}</span>
          </div>

          <div className="track">
            <div
              className="fill"
              style={{
                width: `${(n(x[count]) / max) * 100}%`,
              }}
            />
          </div>

          <div className="barMeta">
            <span>{moneyLabel}</span>
            <b>{money(x[moneyKey])}</b>
          </div>
        </div>
      ))}
    </div>
  );
}

/* =========================================================
   RECOVERY MODAL
========================================================= */

function RecoveryModal({
  opportunity,
  onClose,
  onExecuted,
}) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState(null);
  const [modalError, setModalError] = useState("");

  useEffect(() => {
    let active = true;

    setLoading(true);
    setModalError("");
    setResult(null);
    setDetails(null);

    getRecoveryDetails(
      opportunity.transaction_id
    )
      .then((data) => {
        if (active) {
          setDetails(data);
        }
      })
      .catch((error) => {
        if (active) {
          setModalError(
            error.message ||
              "Unable to load recovery details."
          );
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [opportunity]);

  async function handleExecute() {
    if (!opportunity?.transaction_id) {
      return;
    }

    setExecuting(true);
    setModalError("");
    setResult(null);

    try {
      const response =
        await executeRecovery(
          opportunity.transaction_id
        );

      setResult(response);

      if (onExecuted) {
        await onExecuted(
          opportunity.transaction_id
        );
      }

      /* Refresh modal details so status stays correct */
      const updatedDetails =
        await getRecoveryDetails(
          opportunity.transaction_id
        );

      setDetails(updatedDetails);

    } catch (error) {
      setModalError(
        error.message ||
          "Recovery execution failed."
      );
    } finally {
      setExecuting(false);
    }
  }

  const alreadyExecuted =
    String(
      details?.recovery_status ||
        opportunity?.recovery_status ||
        ""
    ).toUpperCase() === "EXECUTED";

  function getDecisionExplanation() {
    if (!details) {
      return {
        headline: "Analyzing payment...",
        points: [],
      };
    }

    const probability =
      Number(
        details.recovery_probability || 0
      );

    const action =
      String(
        details.recommended_action || ""
      ).toLowerCase();

    const failureCategory =
      nice(
        details.failure_category || ""
      );

    const failureReason =
      nice(
        details.failure_reason || ""
      );

    const paymentMethod =
      nice(
        details.payment_method || ""
      );

    const points = [];

    if (probability >= 0.7) {
      points.push(
        "High recovery probability indicates a strong opportunity to attempt recovery."
      );
    } else if (probability >= 0.5) {
      points.push(
        "Moderate recovery probability suggests the payment is worth attempting to recover."
      );
    } else {
      points.push(
        "Lower recovery probability means the action should be handled with greater caution."
      );
    }

    if (failureCategory) {
      points.push(
        `Failure category: ${failureCategory}.`
      );
    }

    if (failureReason) {
      points.push(
        `Detected failure reason: ${failureReason}.`
      );
    }

    if (paymentMethod) {
      points.push(
        `Original payment method: ${paymentMethod}.`
      );
    }

    if (action.includes("another payment")) {
      points.push(
        "A different payment method is recommended to avoid repeating the same payment-path failure."
      );
    } else if (action.includes("add funds")) {
      points.push(
        "The customer is prompted to add funds before another payment attempt."
      );
    } else if (action.includes("retry")) {
      points.push(
        "A retry is recommended because the payment remains a recoverable opportunity."
      );
    }

    return {
      headline:
        probability >= 0.7
          ? "Strong recovery opportunity"
          : probability >= 0.5
          ? "Moderate recovery opportunity"
          : "Cautious recovery opportunity",
      points,
    };
  }

  const decision =
    getDecisionExplanation();

  return (
    <div
      className="modalBackdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="recoveryModal">

        <div className="modalHeader">
          <div>
            <div className="eyebrow">
              RECOVERY OPPORTUNITY
            </div>

            <h2>
              {opportunity.transaction_id}
            </h2>

            <small>
              Customer{" "}
              {opportunity.customer_id || "—"}
            </small>
          </div>

          <button
            className="closeButton"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        {loading ? (
          <div className="modalLoading">
            Loading recovery intelligence...
          </div>
        ) : modalError ? (
          <div className="modalError">
            {modalError}
          </div>
        ) : details ? (
          <>
            <div className="recoveryHero">

              <div>
                <span>
                  PAYMENT AMOUNT
                </span>

                <strong>
                  {money(details.amount)}
                </strong>
              </div>

              <div>
                <span>
                  RECOVERY PROBABILITY
                </span>

                <strong>
                  {pct(
                    details.recovery_probability
                  )}
                </strong>
              </div>

              <div>
                <span>
                  EXPECTED RECOVERY
                </span>

                <strong>
                  {money(
                    details.expected_recovery_value
                  )}
                </strong>
              </div>

            </div>

            <div className="detailGrid">

              <div>
                <span>Priority</span>
                <Badge
                  p={details.priority}
                />
              </div>

              <div>
                <span>
                  Payment method
                </span>

                <b>
                  {nice(
                    details.payment_method
                  )}
                </b>
              </div>

              <div>
                <span>
                  Failure category
                </span>

                <b>
                  {nice(
                    details.failure_category
                  )}
                </b>
              </div>

              <div>
                <span>
                  Failure reason
                </span>

                <b>
                  {nice(
                    details.failure_reason
                  )}
                </b>
              </div>

            </div>

            <div className="recommendedBox">

              <span>
                AI RECOMMENDATION
              </span>

              <strong>
                {details.recommended_action}
              </strong>

              <p>
                RevenueOS evaluates the
                recovery probability and
                payment failure context to
                determine the recommended
                recovery action.
              </p>

            </div>

            <div className="decisionBox">

              <div className="decisionHeader">
                <div>
                  <span>
                    AI DECISION EXPLANATION
                  </span>

                  <strong>
                    {decision.headline}
                  </strong>
                </div>

                <div className="confidenceBadge">
                  {pct(
                    details.recovery_probability
                  )}

                  <small>
                    confidence
                  </small>
                </div>
              </div>

              <div className="decisionPoints">

                {decision.points.map(
                  (point, index) => (
                    <div
                      className="decisionPoint"
                      key={index}
                    >
                      <span>✓</span>
                      <p>{point}</p>
                    </div>
                  )
                )}

              </div>

            </div>

            {!result &&
            !alreadyExecuted ? (
              <button
                className="executeButton"
                onClick={handleExecute}
                disabled={executing}
              >
                {executing
                  ? "Executing recovery..."
                  : "⚡ Execute Recovery"}
              </button>
            ) : alreadyExecuted ? (
              <div className="resultBox">

                <div className="resultIcon">
                  ✓
                </div>

                <div>
                  <strong>
                    Recovery already executed
                  </strong>

                  <p>
                    This recovery opportunity
                    has already been processed.
                  </p>

                  <small>
                    Action:{" "}
                    {details.recommended_action}
                  </small>
                </div>

              </div>
            ) : (
              <div className="resultBox">

                <div className="resultIcon">
                  ✓
                </div>

                <div>
                  <strong>
                    {result.result ===
                    "RECOVERY_SIMULATED_SUCCESS"
                      ? "Recovery simulated successfully"
                      : "Recovery attempt initiated"}
                  </strong>

                  <p>
                    {result.message ||
                      "Recovery action executed and recorded successfully."}
                  </p>

                  <small>
                    Action:{" "}
                    {result.action ||
                      details.recommended_action}
                  </small>
                </div>

              </div>
            )}

          </>
        ) : null}

      </div>
    </div>
  );
}

/* =========================================================
   OPPORTUNITY TABLE
========================================================= */

function OpportunityTable({
  rows,
  onPriority,
  onView,
  onExecute,
  onReset,
  executingId,
  resettingId,
}) {
  return (
    <section className="card">

      <Header
        eyebrow="ACTION QUEUE"
        title="Highest-value recovery opportunities"
        tag="AI RANKED"
      />

      {!rows.length ? (
        <div className="empty">
          No recovery opportunities available.
        </div>
      ) : (
        <div className="tableWrap">

          <table>
            <thead>
              <tr>
                <th>TRANSACTION</th>
                <th>METHOD</th>
                <th>AMOUNT</th>
                <th>RECOVERY PROB.</th>
                <th>PRIORITY</th>
                <th>ACTION</th>
                <th>EXPECTED RECOVERY</th>
                <th>MANAGE</th>
              </tr>
            </thead>

            <tbody>

              {rows.map((x, i) => {

                const transactionId =
                  x.transaction_id;

                const isExecuting =
                  executingId ===
                  transactionId;

                const isResetting =
                  resettingId ===
                  transactionId;

                const isExecuted =
                  String(
                    x.recovery_status || ""
                  ).toUpperCase() ===
                  "EXECUTED";

                return (
                  <tr
                    key={
                      transactionId || i
                    }
                  >

                    <td>
                      <b>
                        {transactionId || "—"}
                      </b>

                      <small>
                        {x.customer_id || "—"}
                      </small>
                    </td>

                    <td>
                      <span className="method">
                        {x.payment_method || "—"}
                      </span>
                    </td>

                    <td>
                      {money(x.amount)}
                    </td>

                    <td>
                      <div className="prob">

                        <div className="probTrack">
                          <div
                            className="probFill"
                            style={{
                              width: `${Math.min(
                                n(
                                  x.recovery_probability
                                ) * 100,
                                100
                              )}%`,
                            }}
                          />
                        </div>

                        {pct(
                          x.recovery_probability
                        )}

                      </div>
                    </td>

                    <td>
                      <button
                        className="plain"
                        onClick={() =>
                          onPriority?.(
                            x.priority
                          )
                        }
                      >
                        <Badge
                          p={x.priority}
                        />
                      </button>
                    </td>

                    <td>
                      {x.recommended_action ||
                        "Retry payment"}
                    </td>

                    <td>
                      <b className="green">
                        {money(
                          x.expected_recovery_value
                        )}
                      </b>
                    </td>

                    <td>
                      <div className="manageButtons">

                        <button
                          className="viewButton"
                          onClick={() =>
                            onView?.(x)
                          }
                        >
                          View
                        </button>

                        {!isExecuted ? (

                          <button
                            className="executeButton"
                            disabled={
                              isExecuting ||
                              isResetting ||
                              !transactionId
                            }
                            onClick={() =>
                              onExecute?.(
                                transactionId
                              )
                            }
                          >
                            {isExecuting
                              ? "Executing..."
                              : "Execute"}
                          </button>

                        ) : (

                          <button
                            className="resetButton"
                            disabled={
                              isResetting ||
                              !transactionId
                            }
                            onClick={() =>
                              onReset?.(
                                transactionId
                              )
                            }
                          >
                            {isResetting
                              ? "Resetting..."
                              : "↻ Reset"}
                          </button>

                        )}

                      </div>
                    </td>

                  </tr>
                );
              })}

            </tbody>
          </table>

        </div>
      )}

    </section>
  );
}

/* =========================================================
   GENERIC DATA TABLE
========================================================= */

function DataTable({
  title,
  rows,
  headers,
}) {
  return (
    <section className="card">

      <Header
        eyebrow="DATA"
        title={title}
        tag={`${num(rows.length)} SHOWN`}
      />

      {!rows.length ? (
        <div className="empty">
          No data available.
        </div>
      ) : (
        <div className="tableWrap">

          <table>
            <thead>
              <tr>
                {headers.map((h) => (
                  <th key={h}>
                    {nice(h).toUpperCase()}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>

              {rows
                .slice(0, 100)
                .map((r, i) => (
                  <tr
                    key={
                      r.transaction_id ||
                      r.customer_id ||
                      i
                    }
                  >

                    {headers.map((h) => (
                      <td key={h}>

                        {h.includes("amount") ||
                        h.includes("risk") ||
                        (
                          h.includes("recovery") &&
                          h !==
                            "average_recovery_probability"
                        )
                          ? money(r[h])
                          : h ===
                            "average_recovery_probability"
                          ? pct(r[h])
                          : h === "status"
                          ? (
                            <span
                              className={`status ${String(
                                r[h]
                              ).toLowerCase()}`}
                            >
                              {r[h]}
                            </span>
                          )
                          : nice(
                              r[h] ?? "—"
                            )}

                      </td>
                    ))}

                  </tr>
                ))}

            </tbody>
          </table>

        </div>
      )}

    </section>
  );
}

/* =========================================================
   MAIN APP
========================================================= */

export default function App() {
 const [loggedIn, setLoggedIn] = useState(() => {
  return Boolean(localStorage.getItem("revenueos_token"));
});

const handleLogin = () => {
  window.location.reload();
};


const handleLogout = () => {
  localStorage.removeItem("revenueos_token");
  localStorage.removeItem("revenueos_user");
  setLoggedIn(false);
};
  const [page, setPage] =
    useState("Overview");

  const [d, setD] =
    useState(EMPTY);

  const [rows, setRows] =
    useState([]);

  const [recoveryHistory, setRecoveryHistory] =
    useState([]);

  const [payments, setPayments] =
    useState([]);

  const [customers, setCustomers] =
    useState([]);

  const [methods, setMethods] =
    useState([]);

  const [failures, setFailures] =
    useState([]);

  const [analytics, setAnalytics] =
    useState(null);

  const [filter, setFilter] =
    useState("");

  const [search, setSearch] =
    useState("");

  const [status, setStatus] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const [refreshing, setRefreshing] =
    useState(false);

  const [error, setError] =
    useState("");

  const [executingId, setExecutingId] =
    useState(null);

  const [resettingId, setResettingId] =
    useState(null);

  const [
    selectedOpportunity,
    setSelectedOpportunity,
  ] = useState(null);

  /* =======================================================
     LOAD ALL DATA
  ======================================================= */

  const load = useCallback(
    async (refresh = false) => {

      if (refresh) {
        setRefreshing(true);
      }

      try {

        const [
          dashboardData,
          recoveryData,
          paymentData,
          customerData,
          methodData,
          failureData,
          analyticsData,
          historyData,
        ] = await Promise.all([

          getDashboardSummary(),

          getRecoveryOpportunities(
            "",
            100,
            "",
            ""
          ),

          getPayments("", 100),

          getCustomers(100),

          getPaymentMethodAnalytics(),

          getFailureCategoryAnalytics(),

          getAnalyticsOverview(),

          getRecoveryHistory(),

        ]);

        setD(
          normalize(dashboardData)
        );

        setRows(
          Array.isArray(recoveryData)
            ? recoveryData
            : []
        );

        setPayments(
          Array.isArray(paymentData)
            ? paymentData
            : []
        );

        setCustomers(
          Array.isArray(customerData)
            ? customerData
            : []
        );

        setMethods(
          Array.isArray(methodData)
            ? methodData
            : []
        );

        setFailures(
          Array.isArray(failureData)
            ? failureData
            : []
        );

        setAnalytics(
          analyticsData
        );

        setRecoveryHistory(
          Array.isArray(historyData)
            ? historyData
            : Array.isArray(historyData?.data)
            ? historyData.data
            : []
        );

        setError("");

      } catch (x) {

        console.error(
          "Dashboard load failed:",
          x
        );

        setError(
          x.message ||
            "Backend connection failed"
        );

      } finally {

        setLoading(false);
        setRefreshing(false);

      }
    },
    []
  );

  useEffect(() => {
    load(false);
  }, [load]);

  /* =======================================================
     RECOVERY FILTER
  ======================================================= */

  const filterRows = async (
    p = filter,
    searchText = search,
    statusValue = status
  ) => {

    const newPriority = p || "";
    const newSearch = searchText || "";
    const newStatus = statusValue || "";

    setFilter(newPriority);
    setSearch(newSearch);
    setStatus(newStatus);

    try {

      const data =
        await getRecoveryOpportunities(
          newPriority,
          100,
          newSearch,
          newStatus
        );

      setRows(
        Array.isArray(data)
          ? data
          : []
      );

      setPage("Recovery");

    } catch (x) {

      console.error(
        "Failed to load recovery opportunities:",
        x
      );

      setRows([]);

      setError(
        x.message ||
          "Failed to load recovery opportunities."
      );
    }
  };

  /* =======================================================
     REFRESH RECOVERY DATA
  ======================================================= */

  const refreshRecoveryData =
    async () => {

      const [
        updatedRows,
        dashboard,
        updatedMethods,
        updatedFailures,
        updatedAnalytics,
        history,
      ] = await Promise.all([

        getRecoveryOpportunities(
          filter,
          100,
          search,
          status
        ),

        getDashboardSummary(),

        getPaymentMethodAnalytics(),

        getFailureCategoryAnalytics(),

        getAnalyticsOverview(),

        getRecoveryHistory(),

      ]);

      setRows(
        Array.isArray(updatedRows)
          ? updatedRows
          : []
      );

      setD(
        normalize(dashboard)
      );

      setMethods(
        Array.isArray(updatedMethods)
          ? updatedMethods
          : []
      );

      setFailures(
        Array.isArray(updatedFailures)
          ? updatedFailures
          : []
      );

      setAnalytics(
        updatedAnalytics
      );

      setRecoveryHistory(
        Array.isArray(history)
          ? history
          : Array.isArray(history?.data)
          ? history.data
          : []
      );
    };

  /* =======================================================
     EXECUTE RECOVERY FROM TABLE
  ======================================================= */

  const handleExecuteRecovery =
    async (transactionId) => {

      if (!transactionId) {
        return;
      }

      setExecutingId(
        transactionId
      );

      try {

        await executeRecovery(
          transactionId
        );

        await refreshRecoveryData();

        setError("");

      } catch (err) {

        console.error(
          "Recovery execution error:",
          err
        );

        setError(
          err.message ||
            "Recovery execution failed."
        );

      } finally {

        setExecutingId(null);

      }
    };

  /* =======================================================
     RESET RECOVERY TO PENDING
  ======================================================= */

  const handleResetRecovery =
    async (transactionId) => {

      if (!transactionId) {
        return;
      }

      setResettingId(
        transactionId
      );

      try {

        await resetRecovery(
          transactionId
        );

        await refreshRecoveryData();

        setError("");

      } catch (err) {

        console.error(
          "Recovery reset error:",
          err
        );

        setError(
          err.message ||
            "Failed to reset recovery."
        );

      } finally {

        setResettingId(null);

      }
    };

  /* =======================================================
     AFTER MODAL EXECUTION
  ======================================================= */

  const handleModalExecuted =
    async (transactionId) => {

      try {

        await refreshRecoveryData();

        console.log(
          "Recovery completed and data refreshed:",
          transactionId
        );

        setError("");

      } catch (err) {

        console.error(
          "Refresh after recovery failed:",
          err
        );

        setError(
          err.message ||
            "Recovery completed, but refresh failed."
        );
      }
    };

  /* =======================================================
     CALCULATIONS
  ======================================================= */

  const priority =
    d.priority_distribution;

  const total =
    priority.HIGH +
    priority.MEDIUM +
    priority.LOW;

  const sortedMethods =
    useMemo(
      () =>
        [...methods].sort(
          (a, b) =>
            n(b.failed_payments) -
            n(a.failed_payments)
        ),
      [methods]
    );

  const sortedFailures =
    useMemo(
      () =>
        [...failures].sort(
          (a, b) =>
            n(b.failed_payments) -
            n(a.failed_payments)
        ),
      [failures]
    );
if (!loggedIn) {
  return <Login onLogin={handleLogin} />;
}
  /* =======================================================
     LOADING
  ======================================================= */

  if (loading) {
    return (
      <div className="loading">

        <div className="logo">
          R
        </div>

        <h1>
          RevenueOS
        </h1>

        <p>
          Loading recovery
          intelligence...
        </p>

      </div>
    );
  }

  /* =======================================================
     ERROR
  ======================================================= */

  if (
    error &&
    !d.payment_metrics.total_transactions
  ) {
    return (
      <div className="loading">

        <div className="errorCard">

          <div className="errorIcon">
            !
          </div>

          <h1>
            RevenueOS could not
            connect
          </h1>

          <p>
            {error}
          </p>

          <button
            onClick={() =>
              load(false)
            }
          >
            ↻ Retry
          </button>

          <small>
            Start FastAPI at
            https://revenueos-api-hymt.onrender.com
          </small>

        </div>

      </div>
    );
  }

  /* =======================================================
     APP
  ======================================================= */

  return (
    <div className="shell">

      {/* SIDEBAR */}

      <aside className="side">

        <div className="brand">

          <div className="logo small">
            R
          </div>

          <div>
            <b>
              RevenueOS
            </b>

            <span>
              Recovery Intelligence
            </span>
          </div>

        </div>

        <div className="navTitle">
          WORKSPACE
        </div>

        {NAV.map(([x, ic]) => (

          <button
            key={x}
            className={`nav ${
              page === x
                ? "active"
                : ""
            }`}
            onClick={() =>
              setPage(x)
            }
          >
            <i>{ic}</i>
            {x}
          </button>

        ))}

        

        <div className="ai">

          <b>
            <span />
            AI Engine Online
          </b>

          <p>
            Recovery model active
          </p>

          <div>
            ROC-AUC
            <strong>
              0.7155
            </strong>
          </div>

        </div>

        <button
  className="settings"
  onClick={() => setPage("Settings")}
>
  ⚙ Settings
</button>

<button
  className="settings"
  onClick={handleLogout}
>
  ↪ Sign Out
</button>

<small className="version">
  RevenueOS v1.0
</small>

      </aside>

      {/* MAIN */}

      <main className="main">

        <header className="top">

          <div>

            <div className="eyebrow">
              REVENUE RECOVERY
              PLATFORM
            </div>

            <h1>
              {page}
            </h1>

            <p>
              Monitor failed payments
              and prioritize
              high-value recovery
              opportunities.
            </p>

          </div>

          <button
            className="refresh"
            onClick={() =>
              load(true)
            }
            disabled={refreshing}
          >
            {refreshing
              ? "Refreshing..."
              : "↻ Refresh data"}
          </button>

        </header>

        {error && (
          <div className="alert">
            ⚠ {error}
          </div>
        )}

        {/* =================================================
            OVERVIEW
        ================================================= */}

        {page === "Overview" && (
          <>

            <div className="metrics">

              <Metric
                icon="◈"
                title="Total transactions"
                value={num(
                  d.payment_metrics
                    .total_transactions
                )}
                sub="Processed payments"
              />

              <Metric
                icon="×"
                title="Failed payments"
                value={num(
                  d.payment_metrics
                    .failed_payments
                )}
                sub={`${pct(
                  d.payment_metrics
                    .failure_rate
                )} failure rate`}
                tone="danger"
              />

              <Metric
                icon="✓"
                title="Payment success"
                value={pct(
                  d.payment_metrics
                    .success_rate
                )}
                sub={`${num(
                  d.payment_metrics
                    .successful_payments
                )} successful payments`}
                tone="success"
              />

              <Metric
                icon="!"
                title="Revenue at risk"
                value={money(
                  d.recovery_metrics
                    .revenue_at_risk
                )}
                sub={`${pct(
                  d.recovery_metrics
                    .recovery_rate
                )} recovery potential`}
                tone="warn"
              />

            </div>

            <div className="grid2">

              <section className="card">

                <Header
                  eyebrow="PRIORITIZATION"
                  title="Recovery priority"
                  tag="AI SCORED"
                />

                <div className="priorityList">

                  {P.map((x) => {

                    const v =
                      priority[x];

                    const pc =
                      total
                        ? (v / total) * 100
                        : 0;

                    return (
                      <button
                        className="priority"
                        key={x}
                        onClick={() =>
                          filterRows(
                            x,
                            "",
                            ""
                          )
                        }
                      >

                        <div>

                          <span
                            className={`dot ${x.toLowerCase()}`}
                          />

                          <b>{x}</b>

                          <strong>
                            {num(v)}
                          </strong>

                        </div>

                        <div className="track">

                          <div
                            className={`fill ${x.toLowerCase()}`}
                            style={{
                              width: `${pc}%`,
                            }}
                          />

                        </div>

                        <small>
                          {pc.toFixed(1)}%
                          of recovery
                          cases · Click
                          to view
                        </small>

                      </button>
                    );
                  })}

                </div>

                <div className="miniGrid">

                  {P.map((x) => (

                    <button
                      key={x}
                      onClick={() =>
                        filterRows(
                          x,
                          "",
                          ""
                        )
                      }
                    >

                      <span
                        className={`dot ${x.toLowerCase()}`}
                      />

                      {x}

                      <b>
                        {num(
                          priority[x]
                        )}
                      </b>

                    </button>

                  ))}

                </div>

              </section>

              <section className="card">

                <Header
                  eyebrow="PORTFOLIO"
                  title="Priority mix"
                  tag={`${num(
                    total
                  )} CASES`}
                />

                <div className="donutArea">

                  <div
                    className="donut"
                    style={{
                      background:
                        `conic-gradient(#ef4444 0 ${
                          total
                            ? (priority.HIGH /
                                total) *
                              100
                            : 0
                        }%, #f59e0b ${
                          total
                            ? (priority.HIGH /
                                total) *
                              100
                            : 0
                        }% ${
                          total
                            ? ((priority.HIGH +
                                priority.MEDIUM) /
                                total) *
                              100
                            : 0
                        }%, #94a3b8 ${
                          total
                            ? ((priority.HIGH +
                                priority.MEDIUM) /
                                total) *
                              100
                            : 0
                        }% 100%)`,
                    }}
                  >

                    <div>
                      <b>{num(total)}</b>
                      <small>cases</small>
                    </div>

                  </div>

                  <div className="legend">

                    {P.map((x) => (

                      <button
                        key={x}
                        onClick={() =>
                          filterRows(
                            x,
                            "",
                            ""
                          )
                        }
                      >

                        <span
                          className={`dot ${x.toLowerCase()}`}
                        />

                        <div>

                          <b>
                            {nice(x)}
                            {" "}
                            priority
                          </b>

                          <small>
                            {total
                              ? (
                                  (priority[x] /
                                    total) *
                                  100
                                ).toFixed(1)
                              : "0.0"}
                            %
                          </small>

                        </div>

                        <strong>
                          {num(
                            priority[x]
                          )}
                        </strong>

                      </button>

                    ))}

                  </div>

                </div>

              </section>

            </div>

            <div className="grid2">

              <section className="card">

                <Header
                  eyebrow="PAYMENT INTELLIGENCE"
                  title="Payment method exposure"
                  tag="FAILED PAYMENTS"
                />

                <Bars
                  items={sortedMethods}
                  name="payment_method"
                  count="failed_payments"
                  moneyKey="revenue_at_risk"
                  moneyLabel="At risk"
                />

              </section>

              <section className="card">

                <Header
                  eyebrow="FAILURE ANALYTICS"
                  title="Failure categories"
                  tag="TOP PATTERNS"
                />

                <Bars
                  items={sortedFailures}
                  name="failure_category"
                  count="failed_payments"
                  moneyKey="expected_recovery"
                  moneyLabel="Expected recovery"
                />

              </section>

            </div>

            <OpportunityTable
              rows={
                (
                  d.top_opportunities.length
                    ? d.top_opportunities
                    : rows
                )
                  .filter(
                    (x) =>
                      String(
                        x.recovery_status || ""
                      ).toUpperCase() !==
                      "EXECUTED"
                  )
                  .slice(0, 10)
              }
              onPriority={(p) =>
                filterRows(p, "", "")
              }
              onView={
                setSelectedOpportunity
              }
              onExecute={
                handleExecuteRecovery
              }
              onReset={
                handleResetRecovery
              }
              executingId={
                executingId
              }
              resettingId={
                resettingId
              }
            />

          </>
        )}

        {/* =================================================
            RECOVERY
        ================================================= */}

        {page === "Recovery" && (
          <>

            <section className="card">

              <Header
                eyebrow="RECOVERY WORKSPACE"
                title="Recovery opportunities"
                tag={`${num(
                  rows.length
                )} SHOWN`}
              />

              <div className="recoverySearch">

                <input
                  className="searchInput"
                  type="text"
                  placeholder="Search by transaction ID or customer ID"
                  value={search}
                  onChange={(e) => {

                    const value =
                      e.target.value;

                    setSearch(value);

                    filterRows(
                      filter,
                      value,
                      status
                    );

                  }}
                />

              </div>

              <div className="filters">

                Filter by priority:

                <button
                  className={
                    !filter ? "sel" : ""
                  }
                  onClick={() =>
                    filterRows(
                      "",
                      search,
                      status
                    )
                  }
                >
                  ALL
                </button>

                {P.map((x) => (

                  <button
                    className={
                      filter === x
                        ? "sel"
                        : ""
                    }
                    key={x}
                    onClick={() =>
                      filterRows(
                        x,
                        search,
                        status
                      )
                    }
                  >
                    {x}
                  </button>

                ))}

              </div>

              <div className="filters">

                Filter by status:

                <button
                  className={
                    !status ? "sel" : ""
                  }
                  onClick={() =>
                    filterRows(
                      filter,
                      search,
                      ""
                    )
                  }
                >
                  ALL
                </button>

                <button
                  className={
                    status === "PENDING"
                      ? "sel"
                      : ""
                  }
                  onClick={() =>
                    filterRows(
                      filter,
                      search,
                      "PENDING"
                    )
                  }
                >
                  PENDING
                </button>

                <button
                  className={
                    status === "EXECUTED"
                      ? "sel"
                      : ""
                  }
                  onClick={() =>
                    filterRows(
                      filter,
                      search,
                      "EXECUTED"
                    )
                  }
                >
                  EXECUTED
                </button>

              </div>

              <OpportunityTable
                rows={rows}
                onPriority={(p) =>
                  filterRows(
                    p,
                    search,
                    status
                  )
                }
                onView={
                  setSelectedOpportunity
                }
                onExecute={
                  handleExecuteRecovery
                }
                onReset={
                  handleResetRecovery
                }
                executingId={
                  executingId
                }
                resettingId={
                  resettingId
                }
              />

            </section>

            {/* RECOVERY HISTORY */}

            <section className="card">

              <Header
                eyebrow="AUDIT TRAIL"
                title="Recovery History"
                tag="EXECUTED ACTIONS"
              />

              {recoveryHistory.length === 0 ? (
                <div className="historyEmpty">
                  No recovery actions have
                  been executed yet.
                </div>
              ) : (
                <div className="historyTableWrap">

                  <table className="historyTable">

                    <thead>
                      <tr>
                        <th>Transaction</th>
                        <th>Action</th>
                        <th>Result</th>
                        <th>Message</th>
                        <th>Executed At</th>
                      </tr>
                    </thead>

                    <tbody>

                      {recoveryHistory.map(
                        (item, index) => (

                          <tr
                            key={
                              item.id ||
                              item.transaction_id ||
                              index
                            }
                          >

                            <td>
                              {item.transaction_id}
                            </td>

                            <td>
                              {item.action}
                            </td>

                            <td>
                              {item.result}
                            </td>

                            <td>
                              {item.message}
                            </td>

                            <td>
                              {item.executed_at
                                ? new Date(
                                    item.executed_at
                                  ).toLocaleString()
                                : "-"}
                            </td>

                          </tr>

                        )
                      )}

                    </tbody>

                  </table>

                </div>
              )}

            </section>

          </>
        )}

        {/* =================================================
            PAYMENTS
        ================================================= */}

        {page === "Payments" && (
          <>

            <div className="metrics">

              <Metric
                icon="◈"
                title="Transactions"
                value={num(
                  d.payment_metrics
                    .total_transactions
                )}
                sub="All processed payments"
              />

              <Metric
                icon="✓"
                title="Successful"
                value={num(
                  d.payment_metrics
                    .successful_payments
                )}
                sub={pct(
                  d.payment_metrics
                    .success_rate
                )}
                tone="success"
              />

              <Metric
                icon="×"
                title="Failed"
                value={num(
                  d.payment_metrics
                    .failed_payments
                )}
                sub={pct(
                  d.payment_metrics
                    .failure_rate
                )}
                tone="danger"
              />

              <Metric
                icon="₹"
                title="Transaction value"
                value={money(
                  d.payment_metrics
                    .total_transaction_value
                )}
                sub="Processed payment value"
              />

            </div>

            <DataTable
              title="Recent payment activity"
              rows={payments}
              headers={[
                "transaction_id",
                "customer_id",
                "payment_method",
                "amount",
                "status",
                "failure_reason",
              ]}
            />

          </>
        )}

        {/* =================================================
            CUSTOMERS
        ================================================= */}

        {page === "Customers" && (
          <DataTable
            title="Customers with recovery exposure"
            rows={customers}
            headers={[
              "customer_id",
              "failed_payments",
              "revenue_at_risk",
              "expected_recovery",
              "average_recovery_probability",
            ]}
          />
        )}

        {/* =================================================
            ANALYTICS
        ================================================= */}

        {page === "Analytics" && (
          <>

            <div className="metrics">

              <Metric
                icon="×"
                title="Failure rate"
                value={pct(
                  analytics?.failure_rate
                )}
                sub={`${num(
                  analytics?.failed_payments
                )} failed payments`}
                tone="danger"
              />

              <Metric
                icon="!"
                title="Revenue at risk"
                value={money(
                  analytics?.revenue_at_risk
                )}
                sub="Failed-payment exposure"
                tone="warn"
              />

              <Metric
                icon="↗"
                title="Expected recovery"
                value={money(
                  analytics?.expected_recovery
                )}
                sub="AI recovery potential"
                tone="success"
              />

              <Metric
                icon="◎"
                title="Recovery rate"
                value={pct(
                  analytics?.recovery_rate
                )}
                sub="Expected / at risk"
              />

            </div>

            <div className="grid2">

              <section className="card">

                <Header
                  eyebrow="PAYMENT METHODS"
                  title="Failure exposure"
                />

                <Bars
                  items={sortedMethods}
                  name="payment_method"
                  count="failed_payments"
                  moneyKey="revenue_at_risk"
                  moneyLabel="At risk"
                />

              </section>

              <section className="card">

                <Header
                  eyebrow="FAILURE ANALYTICS"
                  title="Category breakdown"
                />

                <Bars
                  items={sortedFailures}
                  name="failure_category"
                  count="failed_payments"
                  moneyKey="expected_recovery"
                  moneyLabel="Expected recovery"
                />

              </section>

            </div>

          </>
        )}

        {/* =================================================
            SETTINGS
        ================================================= */}

        {page === "Settings" && (
  <section className="page">
    <div className="pageHeader">
      <div>
        <h1>Settings</h1>
        <p>Manage your RevenueOS platform preferences</p>
      </div>
    </div>

    <div className="settingsGrid">

      {/* Account */}
      <div className="settingsCard">
        <h3>👤 Account</h3>
        <p className="settingsDescription">
          Current administrator account
        </p>

        <div className="settingRow">
          <div>
            <strong>
              {JSON.parse(
                localStorage.getItem("revenueos_user") || "{}"
              ).email || "admin@revenueos.com"}
            </strong>
            <span>Administrator</span>
          </div>
        </div>
      </div>

      {/* AI Engine */}
      <div className="settingsCard">
        <h3>🤖 AI Recovery Engine</h3>
        <p className="settingsDescription">
          Recovery prediction model configuration
        </p>

        <div className="settingRow">
          <div>
            <strong>Recovery Model</strong>
            <span>Active</span>
          </div>

          <span className="statusBadge success">
            ● Online
          </span>
        </div>

        <div className="settingRow">
          <div>
            <strong>ROC-AUC</strong>
            <span>Model performance</span>
          </div>

          <strong>0.7155</strong>
        </div>
      </div>

      {/* Notifications */}
      <div className="settingsCard">
        <h3>🔔 Notifications</h3>
        <p className="settingsDescription">
          Configure recovery alerts
        </p>

        <div className="settingRow">
          <div>
            <strong>Recovery Alerts</strong>
            <span>Notify when high-value opportunities are detected</span>
          </div>

          <label className="toggle">
            <input type="checkbox" defaultChecked />
            <span className="slider"></span>
          </label>
        </div>
      </div>

      {/* Auto Recovery */}
      <div className="settingsCard">
        <h3>⚡ Recovery Automation</h3>
        <p className="settingsDescription">
          Control automated recovery execution
        </p>

        <div className="settingRow">
          <div>
            <strong>Auto Recovery Mode</strong>
            <span>
              Automatically execute eligible recovery actions
            </span>
          </div>

          <label className="toggle">
            <input type="checkbox" />
            <span className="slider"></span>
          </label>
        </div>

        <div className="warningBox">
          ⚠ Automated recovery is disabled by default.
          Manual approval is required.
        </div>
      </div>

    </div>
  </section>
)}
      </main>

      {/* =================================================
          RECOVERY MODAL
      ================================================= */}

      {selectedOpportunity && (

        <RecoveryModal
          opportunity={
            selectedOpportunity
          }

          onClose={() =>
            setSelectedOpportunity(
              null
            )
          }

          onExecuted={
            handleModalExecuted
          }
        />

      )}

    </div>
  );
}