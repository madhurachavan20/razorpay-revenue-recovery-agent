const API_BASE_URL = "http://127.0.0.1:8000";

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

export const getDashboardSummary = () =>
  request("/dashboard/summary");

export const getPaymentSummary = () =>
  request("/payments/summary");

export const getRecoveryOpportunities = async (
  priority = "",
  limit = 50
) => {
  const params = new URLSearchParams({
    limit: String(limit),
  });

  if (priority) {
    params.set("priority", priority);
  }

  const response = await request(
    `/recovery-opportunities?${params.toString()}`
  );

  return response.data || [];
};

export const getPayments = async (
  status = "",
  limit = 100
) => {
  const params = new URLSearchParams({
    limit: String(limit),
  });

  if (status) {
    params.set("status", status);
  }

  const response = await request(
    `/payments?${params.toString()}`
  );

  return response.data || [];
};

export const getCustomers = async (limit = 100) => {
  const response = await request(
    `/customers?limit=${limit}`
  );

  return response.data || [];
};

export const getAnalyticsOverview = () =>
  request("/analytics/overview");

export const getPaymentMethodAnalytics = () =>
  request("/analytics/payment-methods");

export const getFailureCategoryAnalytics = () =>
  request("/analytics/failure-categories");