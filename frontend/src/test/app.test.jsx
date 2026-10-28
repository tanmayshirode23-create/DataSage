import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App.jsx";
import ReportPage from "../pages/ReportPage.jsx";
import { formatDate } from "../utils.js";

const report = {
  total_rows: 100, total_columns: 5, quality_score: 87.7, score_label: "Needs light cleanup", issue_count: 61,
  duplicate_rows: 2, duplicate_ids: 3, missing_values: 10,
  issue_summary: [{ issue: "Missing values", count: 10 }, { issue: "Duplicate rows", count: 2 }],
  missing_by_column: [{ column: "email", count: 4 }, { column: "phone", count: 0 }],
  invalid_emails: { email: 5 }, invalid_phones: { phone: 2 },
  dates: { signup_date: { missing: 1, invalid: 2 } },
  status: {
    column: "onboarding_status", missing: 1, label_mismatch: 2, non_standard: 3,
    table: [{ current_value: "in-progress", recommended_value: "Needs review", rows: 3, issue_type: "Non-standard value" }],
    distribution: [{ status: "Pending", count: 5 }],
  },
  date_trend: { column: "signup_date", points: [{ month: "2026-01", count: 5 }, { month: "2026-02", count: 7 }] },
  detected_columns: { id_column: "customer_id" },
  recommendations: [{ priority: "High", title: "Complete required fields", detail: "Review missing values in: email." }],
  issues_truncated: false,
};
const dataset = {
  id: 7, filename: "customers.csv", uploaded_at: "2026-10-20T10:00:00", total_rows: 100, total_columns: 5,
  quality_score: 87.7, score_label: "Needs light cleanup", issue_count: 61, below_threshold: true, report,
};

function mockFetch(routes) {
  globalThis.fetch = vi.fn(async (url) => {
    const key = Object.keys(routes).find((k) => String(url).startsWith(k));
    const body = key ? routes[key] : { detail: "Not found" };
    return { ok: Boolean(key), status: key ? 200 : 404, json: async () => body };
  });
}

beforeEach(() => localStorage.clear());
afterEach(() => cleanup());

describe("login flow", () => {
  it("shows the login form when logged out", () => {
    render(<MemoryRouter initialEntries={["/"]}><App /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Log in" })).toBeInTheDocument();
  });

  it("shows the server's error message on a bad login", async () => {
    globalThis.fetch = vi.fn(async () => ({ ok: false, status: 401, json: async () => ({ detail: "Email or password is incorrect." }) }));
    render(<MemoryRouter initialEntries={["/login"]}><App /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrongpass" } });
    fireEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Email or password is incorrect.");
  });

  it("switches to sign up", () => {
    render(<MemoryRouter initialEntries={["/login"]}><App /></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "Create an account" }));
    expect(screen.getByRole("heading", { name: "Create your account" })).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toBeInTheDocument();
  });
});

describe("report page", () => {
  function renderReport() {
    mockFetch({
      "/api/datasets/7/issues": { total: 1, page: 1, page_size: 25, items: [{ row_number: 5, column: "email", issue_type: "invalid_email", value: "bad@@x" }] },
      "/api/datasets/7/preview": { columns: ["customer_id", "email"], rows: [{ row_number: 2, values: { customer_id: 1, email: "bad" }, issues: [{ column: "email", issue_type: "invalid_email" }] }] },
      "/api/datasets/7": dataset,
    });
    render(
      <MemoryRouter initialEntries={["/datasets/7"]}>
        <Routes><Route path="/datasets/:id" element={<ReportPage />} /></Routes>
      </MemoryRouter>
    );
  }

  it("shows the score, label and alert flag", async () => {
    renderReport();
    expect(await screen.findByText("87.7")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Needs light cleanup" })).toBeInTheDocument();
    expect(screen.getByText("Below your alert level.")).toBeInTheDocument();
  });

  it("walks through every tab without crashing", async () => {
    renderReport();
    await screen.findByText("87.7");

    fireEvent.click(screen.getByRole("tab", { name: "Rows" }));
    expect(await screen.findByText("bad")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Issue list" }));
    expect(await screen.findByText("bad@@x")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Checks" }));
    expect(screen.getByText("Missing values", { selector: "h3" })).toBeInTheDocument();
    expect(screen.getByText("in-progress")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Cleanup plan" }));
    expect(screen.getByText("Complete required fields")).toBeInTheDocument();
    // one button in the page header, one inside the plan tab
    expect(screen.getAllByRole("button", { name: "Download cleaned CSV" })).toHaveLength(2);
  });

  it("shows a clear message when the dataset is not found", async () => {
    mockFetch({});
    render(
      <MemoryRouter initialEntries={["/datasets/99"]}>
        <Routes><Route path="/datasets/:id" element={<ReportPage />} /></Routes>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});

describe("utils", () => {
  it("formats server dates", () => {
    expect(formatDate("2026-10-20T10:00:00")).toMatch(/2026/);
    expect(formatDate(null)).toBe("");
  });
});


describe("DataSage shell and dashboard", () => {
  const list = [
    { id: 1, filename: "a.csv", uploaded_at: "2026-10-20T10:00:00", total_rows: 100, total_columns: 5, quality_score: 90, score_label: "Needs light cleanup", issue_count: 40, below_threshold: false },
    { id: 2, filename: "b.csv", uploaded_at: "2026-10-21T10:00:00", total_rows: 50, total_columns: 4, quality_score: 60, score_label: "Migration risk", issue_count: 80, below_threshold: true },
  ];

  function renderLoggedIn(path = "/") {
    localStorage.setItem("dq_token", "t");
    localStorage.setItem("dq_user", JSON.stringify({ id: 1, name: "Tanmay Shirode", email: "t@example.com", alert_threshold: 70 }));
    mockFetch({ "/api/datasets/trends": [], "/api/datasets": list });
    render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>);
  }

  it("shows the DataSage sidebar with the user", async () => {
    renderLoggedIn();
    expect(screen.getAllByText("DataSage").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Datasets" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByText("Tanmay Shirode")).toBeInTheDocument();
  });

  it("summarises all datasets in the summary strip", async () => {
    renderLoggedIn();
    const strip = await screen.findByLabelText("Summary of all datasets");
    expect(strip).toHaveTextContent("Files checked2");
    expect(strip).toHaveTextContent("Average score75.0");   // (90 + 60) / 2
    expect(strip).toHaveTextContent("Below your alert level1");
    expect(strip).toHaveTextContent("Issues found120");
  });

  it("labels each file with a status badge", async () => {
    renderLoggedIn();
    expect(await screen.findByText("Migration risk")).toBeInTheDocument();
    // once in the summary strip, once as the flag on the file's own row
    expect(screen.getAllByText("Below your alert level")).toHaveLength(2);
  });

  it("opens the settings page", async () => {
    renderLoggedIn("/settings");
    expect(await screen.findByRole("heading", { name: "Alert level" })).toBeInTheDocument();
    expect(screen.getByLabelText("Alert score")).toHaveValue(70);
  });
});

describe("zone colors", () => {
  it("picks the right readiness zone", async () => {
    const { zoneFor } = await import("../utils.js");
    expect(zoneFor(50).label).toBe("Migration risk");
    expect(zoneFor(70).label).toBe("Needs focused cleanup");
    expect(zoneFor(87.7).label).toBe("Needs light cleanup");
    expect(zoneFor(95).label).toBe("Launch ready");
  });
});
