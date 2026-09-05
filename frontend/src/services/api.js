const API_BASE_URL = "https://revenueos-api-hymt.onrender.com";

/* =========================================================
   GENERIC REQUEST
========================================================= */

async function request(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;

    try {
      const data = await response.json();

      if (data?.detail) {
        message = data.detail;
      }
    } catch {
      // Ignore invalid JSON
    }

    throw new Error(message);
  }

  return response.json();
}

/* =========================================================
   DASHBOARD
========================================================= */

export const getDashboardSummary = () =>
  request("/dashboard/summary");

/* =========================================================
   PAYMENTS
========================================================= */

export const getPaymentSummary = () =>
  request("/payments/summary");

export const getPayments = async (status = "", limit = 100) => {
  const params = new URLSearchParams({
    limit: String(limit),
  });

  if (status) {
    params.set("status", status);
  }

  const response = await request(
    `/payments?${params.toString()}`
  );

  return Array.isArray(response)
    ? response
    : response?.data || [];
};

/* =========================================================
   RECOVERY OPPORTUNITIES
========================================================= */

export const getRecoveryOpportunities = async (
  priority = "",
  limit = 50,
  search = "",
  status = ""
) => {
  const params = new URLSearchParams({
    limit: String(limit),
  });

  if (priority) {
    params.set("priority", priority);
  }

  if (search.trim()) {
    params.set("search", search.trim());
  }

  if (status) {
    params.set("status", status);
  }

  const response = await request(
    `/recovery-opportunities?${params.toString()}`
  );

  return Array.isArray(response)
    ? response
    : response?.data || [];
};

/* =========================================================
   CUSTOMERS
========================================================= */

export const getCustomers = async (limit = 100) => {
  const response = await request(
    `/customers?limit=${limit}`
  );

  return Array.isArray(response)
    ? response
    : response?.data || [];
};

/* =========================================================
   ANALYTICS
========================================================= */

export const getAnalyticsOverview = () =>
  request("/analytics/overview");

export const getPaymentMethodAnalytics = () =>
  request("/analytics/payment-methods");

export const getFailureCategoryAnalytics = () =>
  request("/analytics/failure-categories");

/* =========================================================
   RECOVERY DETAILS
========================================================= */

export const getRecoveryDetails = (transactionId) =>
  request(
    `/recovery/${encodeURIComponent(
      transactionId
    )}/details`
  );

/* =========================================================
   EXECUTE RECOVERY
========================================================= */

export const executeRecovery = (transactionId) =>
  fetch(
    `${API_BASE_URL}/recovery/${encodeURIComponent(
      transactionId
    )}/execute`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    }
  ).then(async (response) => {
    let data = {};

    try {
      data = await response.json();
    } catch {
      data = {};
    }

    if (!response.ok) {
      throw new Error(
        data?.detail || "Recovery execution failed."
      );
    }

    return data;
  });

/* =========================================================
   RECOVERY HISTORY
========================================================= */

export const getRecoveryHistory = async () => {
  const response = await request("/recovery-history");

  return Array.isArray(response)
    ? response
    : response?.data || [];
};

/* =========================================================
   RESET RECOVERY
========================================================= */

export const resetRecovery = (transactionId) =>
  fetch(
    `${API_BASE_URL}/recovery/${encodeURIComponent(
      transactionId
    )}/reset`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    }
  ).then(async (response) => {
    let data = {};

    try {
      data = await response.json();
    } catch {
      // Ignore invalid JSON
    }

    if (!response.ok) {
      throw new Error(
        data?.detail || "Failed to reset recovery."
      );
    }

    return data;
  });

/* =========================================================
   AUTHENTICATION
========================================================= */

export const login = async (email, password) => {
  const response = await fetch(
    `${API_BASE_URL}/auth/login`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        password,
      }),
    }
  );

  let data = {};

  try {
    data = await response.json();
  } catch {
    // Ignore invalid JSON
  }

  if (!response.ok) {
    throw new Error(
      data?.detail || "Login failed."
    );
  }

  return data;
};