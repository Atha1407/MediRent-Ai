
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from "recharts";

import React from "react";

import {
  Activity,
  TrendingUp,
  IndianRupee,
  Package,
  HeartPulse,
  LayoutDashboard,
  ClipboardCheck,
  ArrowUpRight
} from "lucide-react";

import {
  BrowserRouter,
  Routes,
  Route,
  NavLink,
  Outlet
} from "react-router-dom";

import "./App.css";

const navigation = [
  { label: "Overview", path: "/", icon: LayoutDashboard },
  { label: "Demand Prediction", path: "/demand", icon: TrendingUp },
  { label: "Equipment Utilisation", path: "/utilisation", icon: Activity },
  { label: "Revenue Prediction", path: "/revenue", icon: IndianRupee },
  { label: "Smart Allocation", path: "/allocation", icon: ClipboardCheck }
];

const metrics = [
  {
    title: "Active Rentals",
    value: "42",
    description: "Currently rented equipment",
    icon: Package
  },
  {
    title: "Equipment Utilisation",
    value: "78%",
    description: "Illustrative utilisation",
    icon: Activity
  },
  {
    title: "Predicted Demand",
    value: "126",
    description: "Illustrative forecast",
    icon: TrendingUp
  },
  {
    title: "Expected Revenue",
    value: "₹5,26,536",
    description: "Illustrative forecast",
    icon: IndianRupee
  }
];

function DashboardLayout() {
  return (
    <div className="dashboard">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <HeartPulse size={25} />
          </div>
          <div>
            <h2>MediRent AI</h2>
            <p>Healthcare Intelligence</p>
          </div>
        </div>

        <p className="nav-label">WORKSPACE</p>

        <nav className="navigation">
          {navigation.map(({ label, path, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              end={path === "/"}
              className={({ isActive }) =>
                `nav-item ${isActive ? "active" : ""}`
              }
            >
              <Icon size={19} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <span className="online-dot" />
          Newlife Healthcare
          <p>Medical Equipment Intelligence</p>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">NEWLIFE HEALTHCARE / ANALYTICS</p>
            <h2>Business Intelligence</h2>
          </div>

          <div className="profile">
            <div className="profile-avatar">NH</div>
            <div>
              <strong>Administrator</strong>
              <p>Healthcare Operations</p>
            </div>
          </div>
        </header>

        <section className="content">
          <Outlet />
          <footer className="footer">
            <span>MediRent AI · Newlife Healthcare</span>
            <span>AI-Powered Business Intelligence</span>
          </footer>
        </section>
      </main>
    </div>
  );
}

function Overview() {
  return (
    <>
      <div className="welcome">
        <div>
          <span className="welcome-tag">YOUR BUSINESS AT A GLANCE</span>
          <h1>Dashboard Overview</h1>
          <p>
            Monitor equipment, forecast demand and make smarter rental
            decisions.
          </p>
        </div>
        <div className="date-label">Analytics Workspace</div>
      </div>

      <div className="section-heading">
        <h2>Performance Summary</h2>
        <p>Key indicators for your rental business</p>
      </div>

      <div className="metrics-grid">
        {metrics.map(({ title, value, description, icon: Icon }) => (
          <article className="metric-card" key={title}>
            <div className="metric-top">
              <span>{title}</span>
              <div className="metric-icon">
                <Icon size={21} />
              </div>
            </div>
            <h3>{value}</h3>
            <p className="metric-description">{description}</p>
            <div className="metric-footer">
              <ArrowUpRight size={15} />
              <span>Business intelligence</span>
            </div>
          </article>
        ))}
      </div>

      <div className="lower-grid">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <h2>Demand & Forecasting</h2>
              <p>Illustrative demand visualization</p>
            </div>
            <TrendingUp size={22} />
          </div>

          <div className="chart-placeholder">
            <div className="chart-bars">
              {[42, 56, 48, 68, 62, 80, 72, 92, 76, 100, 86, 96].map(
                (height, index) => (
                  <div
                    className={`chart-bar ${index >= 8 ? "forecast" : ""}`}
                    style={{ height: `${height}%` }}
                    key={index}
                  />
                )
              )}
            </div>
            <div className="chart-months">
              <span>Jan</span><span>Mar</span><span>May</span>
              <span>Jul</span><span>Sep</span><span>Nov</span>
            </div>
          </div>

          <p className="demo-note">
            Demo visualization. Actual model outputs will be connected later.
          </p>
        </article>

        <article className="panel insight-panel">
          <div className="panel-heading">
            <div>
              <h2>Decision Insights</h2>
              <p>Supporting smarter rental operations</p>
            </div>
            <HeartPulse size={22} />
          </div>

          {[
            ["01", "Demand Prediction", "Understand future equipment requirements."],
            ["02", "Equipment Utilisation", "Review equipment usage and availability."],
            ["03", "Smart Allocation", "Find suitable units for rental requests."]
          ].map(([number, title, description]) => (
            <div className="insight-item" key={number}>
              <span className="insight-number">{number}</span>
              <div>
                <h3>{title}</h3>
                <p>{description}</p>
              </div>
            </div>
          ))}
        </article>
      </div>
    </>
  );
}

function FeaturePage({ title, description, children }) {
  return (
    <div className="feature-page">
      <span className="welcome-tag">MEDIRENT AI / ANALYTICS</span>
      <h1>{title}</h1>
      <p>{description}</p>
      <div className="panel feature-panel">
        {children}
      </div>
    </div>
  );
}


function DemandChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart
        data={data}
        margin={{ top: 10, right: 20, left: 0, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
        <XAxis
          dataKey="month"
          tick={{ fill: "#64748B", fontSize: 12 }}
          axisLine={{ stroke: "#CBD5E1" }}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fill: "#64748B", fontSize: 12 }}
          axisLine={false}
        />
        <Tooltip />
        <Legend />
        <Line
          type="monotone"
          dataKey="actual"
          name="Historical"
          stroke="#0F766E"
          strokeWidth={3}
          connectNulls={false}
          dot={{ r: 4 }}
        />
        <Line
          type="monotone"
          dataKey="predicted"
          name="Forecast"
          stroke="#D97706"
          strokeWidth={3}
          strokeDasharray="6 4"
          connectNulls={false}
          dot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function Demand() {
  const [equipment, setEquipment] = React.useState("All Equipment");
  const [period, setPeriod] = React.useState("6");

  const allData = [
    { month: "May", wheelchair: 42, oxygen: 30, bed: 25 },
    { month: "Jun", wheelchair: 48, oxygen: 35, bed: 29 },
    { month: "Jul", wheelchair: 45, oxygen: 38, bed: 32 },
    { month: "Aug", wheelchair: 55, oxygen: 40, bed: 35 },
    { month: "Sep", wheelchair: 60, oxygen: 46, bed: 39 },
    { month: "Oct", wheelchair: 65, oxygen: 50, bed: 43 },
    { month: "Nov", wheelchair: 70, oxygen: 54, bed: 47 },
    { month: "Dec", wheelchair: 74, oxygen: 58, bed: 51 },
    { month: "Jan", wheelchair: 78, oxygen: 62, bed: 55 },
    { month: "Feb", wheelchair: 82, oxygen: 66, bed: 59 },
    { month: "Mar", wheelchair: 88, oxygen: 70, bed: 63 },
    { month: "Apr", wheelchair: 92, oxygen: 75, bed: 68 }
  ];

  const data = allData.slice(-Number(period)).map((item, index, array) => {
    const historical = index < array.length - 2;

    if (equipment === "Wheelchair") {
      return {
        month: item.month,
        actual: historical ? item.wheelchair : null,
        predicted: !historical ? item.wheelchair : null
      };
    }

    if (equipment === "Oxygen Concentrator") {
      return {
        month: item.month,
        actual: historical ? item.oxygen : null,
        predicted: !historical ? item.oxygen : null
      };
    }

    if (equipment === "Hospital Bed") {
      return {
        month: item.month,
        actual: historical ? item.bed : null,
        predicted: !historical ? item.bed : null
      };
    }

    return {
      month: item.month,
      actual: historical
        ? item.wheelchair + item.oxygen + item.bed
        : null,
      predicted: !historical
        ? item.wheelchair + item.oxygen + item.bed
        : null
    };
  });

  const totalDemand = data.reduce(
    (sum, item) => sum + (item.actual ?? item.predicted ?? 0),
    0
  );

  return (
    <FeaturePage
      title="Demand Prediction"
      description="Explore historical and forecast equipment demand."
    >
      <div className="demand-toolbar">
        <div>
          <label htmlFor="demand-equipment">Equipment type</label>
          <select
            id="demand-equipment"
            value={equipment}
            onChange={(event) => setEquipment(event.target.value)}
          >
            <option>All Equipment</option>
            <option>Wheelchair</option>
            <option>Oxygen Concentrator</option>
            <option>Hospital Bed</option>
          </select>
        </div>

        <div>
          <label htmlFor="demand-period">Time period</label>
          <select
            id="demand-period"
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
          >
            <option value="6">Last 6 months</option>
            <option value="12">Last 12 months</option>
          </select>
        </div>
      </div>

      <div className="demand-summary">
        <div>
          <span>Equipment selection</span>
          <strong>{equipment}</strong>
        </div>
        <div>
          <span>Displayed data points</span>
          <strong>{data.length}</strong>
        </div>
        <div>
          <span>Total displayed demand</span>
          <strong>{totalDemand.toLocaleString("en-IN")}</strong>
        </div>
      </div>

      <div className="demand-chart">
        <div className="chart-title">
          <div>
            <h2>Historical vs Forecast Demand</h2>
            <p>Illustrative equipment demand over time</p>
          </div>
          <span className="demo-badge">SAMPLE DATA</span>
        </div>

        <div className="chart-legend">
          <span><i className="legend-dot actual-dot" /> Historical</span>
          <span><i className="legend-dot forecast-dot" /> Forecast</span>
        </div>

        <div style={{ width: "100%", height: 320 }}>
          <DemandChart data={data} />
        </div>

        <p className="demo-warning">
          These values are illustrative UI data, not predictions from your
          AIML model. The historical/forecast split is for demonstration;
          replace it with actual dates and API results during integration.
        </p>
      </div>
    </FeaturePage>
  );
}


function Utilisation() {
  const [category, setCategory] = React.useState("All Equipment");
  const [period, setPeriod] = React.useState("This Month");

  const equipment = [
    { name: "Wheelchairs", category: "Mobility", total: 40, rented: 31 },
    { name: "Oxygen Concentrators", category: "Respiratory", total: 30, rented: 24 },
    { name: "Hospital Beds", category: "Patient Care", total: 25, rented: 18 },
    { name: "Patient Monitors", category: "Monitoring", total: 20, rented: 12 },
    { name: "Suction Machines", category: "Respiratory", total: 15, rented: 9 }
  ];

  const filtered = equipment.filter(
    (item) => category === "All Equipment" || item.category === category
  );

  const total = filtered.reduce((sum, item) => sum + item.total, 0);
  const rented = filtered.reduce((sum, item) => sum + item.rented, 0);
  const available = total - rented;
  const utilisation = total ? Math.round((rented / total) * 100) : 0;

  return (
    <FeaturePage
      title="Equipment Utilisation"
      description="Monitor equipment usage, availability and rental distribution."
    >
      <div className="util-toolbar">
        <div>
          <label htmlFor="util-category">Equipment category</label>
          <select
            id="util-category"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
          >
            <option>All Equipment</option>
            <option>Mobility</option>
            <option>Respiratory</option>
            <option>Patient Care</option>
            <option>Monitoring</option>
          </select>
        </div>

        <div>
          <label htmlFor="util-period">Reporting period</label>
          <select
            id="util-period"
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
          >
            <option>This Month</option>
            <option>Last 3 Months</option>
            <option>Last 6 Months</option>
          </select>
        </div>
      </div>

      <div className="util-demo-note">
        DEMO DATA · Reporting period: {period}
      </div>

      <div className="util-kpi-grid">
        <article className="util-kpi">
          <span>Total Equipment</span>
          <strong>{total}</strong>
          <p>Units in selected category</p>
        </article>

        <article className="util-kpi">
          <span>Currently Rented</span>
          <strong>{rented}</strong>
          <p>Illustrative rental count</p>
        </article>

        <article className="util-kpi">
          <span>Available Units</span>
          <strong>{available}</strong>
          <p>Not currently rented in sample</p>
        </article>

        <article className="util-kpi">
          <span>Utilisation Rate</span>
          <strong>{utilisation}%</strong>
          <p>Rented units / total units</p>
        </article>
      </div>

      <div className="util-table-panel">
        <div className="chart-title">
          <div>
            <h2>Equipment Breakdown</h2>
            <p>Rental and availability by equipment type</p>
          </div>
        </div>

        <div className="util-table-scroll">
          <table className="util-table">
            <thead>
              <tr>
                <th>Equipment</th>
                <th>Total Units</th>
                <th>Rented</th>
                <th>Available</th>
                <th>Utilisation</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => {
                const rate = Math.round((item.rented / item.total) * 100);

                return (
                  <tr key={item.name}>
                    <td>
                      <strong>{item.name}</strong>
                      <small>{item.category}</small>
                    </td>
                    <td>{item.total}</td>
                    <td>{item.rented}</td>
                    <td>{item.total - item.rented}</td>
                    <td>
                      <div className="util-rate">
                        <strong>{rate}%</strong>
                        <div className="util-track">
                          <div style={{ width: `${rate}%` }} />
                        </div>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <p className="demo-warning">
          Illustrative figures only. Connect the equipment inventory and rental
          database before using this page for operational decisions.
        </p>
      </div>
    </FeaturePage>
  );
}

function RevenueChart({ data }) {
  const formatRupees = (value) =>
    `₹${Number(value).toLocaleString("en-IN")}`;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart
        data={data}
        margin={{ top: 10, right: 20, left: 15, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />

        <XAxis
          dataKey="month"
          tick={{ fill: "#64748B", fontSize: 12 }}
        />

        <YAxis
          tickFormatter={(value) => `₹${Math.round(value / 1000)}k`}
          tick={{ fill: "#64748B", fontSize: 12 }}
          width={65}
        />

        <Tooltip
          formatter={(value) => formatRupees(value)}
        />

        <Legend />

        <Line
          type="monotone"
          dataKey="actual"
          name="Historical Revenue"
          stroke="#0F766E"
          strokeWidth={3}
          connectNulls={false}
          dot={{ r: 4 }}
        />

        <Line
          type="monotone"
          dataKey="predicted"
          name="Forecast Revenue"
          stroke="#D97706"
          strokeWidth={3}
          strokeDasharray="6 4"
          connectNulls={false}
          dot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}



function Revenue() {
  const [category, setCategory] = React.useState("All Equipment");
  const [period, setPeriod] = React.useState("6");

  const revenueData = [
    { month: "May", wheelchair: 42000, oxygen: 65000, bed: 78000 },
    { month: "Jun", wheelchair: 46000, oxygen: 69000, bed: 82000 },
    { month: "Jul", wheelchair: 44000, oxygen: 72000, bed: 80000 },
    { month: "Aug", wheelchair: 51000, oxygen: 76000, bed: 86000 },
    { month: "Sep", wheelchair: 55000, oxygen: 81000, bed: 91000 },
    { month: "Oct", wheelchair: 59000, oxygen: 85000, bed: 96000 },
    { month: "Nov", wheelchair: 62000, oxygen: 89000, bed: 101000 },
    { month: "Dec", wheelchair: 66000, oxygen: 94000, bed: 106000 },
    { month: "Jan", wheelchair: 70000, oxygen: 98000, bed: 111000 },
    { month: "Feb", wheelchair: 73000, oxygen: 103000, bed: 115000 },
    { month: "Mar", wheelchair: 77000, oxygen: 108000, bed: 121000 },
    { month: "Apr", wheelchair: 81000, oxygen: 113000, bed: 126000 }
  ];

  const categories = [
    { label: "Wheelchairs", key: "wheelchair" },
    { label: "Oxygen Concentrators", key: "oxygen" },
    { label: "Hospital Beds", key: "bed" }
  ];

  const filteredData = revenueData.slice(-Number(period)).map(
    (item, index, array) => {
      const historical = index < array.length - 2;

      const actualValue =
        category === "All Equipment"
          ? item.wheelchair + item.oxygen + item.bed
          : item[category];

      return {
        month: item.month,
        actual: historical ? actualValue : null,
        predicted: !historical ? actualValue : null
      };
    }
  );

  const historicalRevenue = filteredData.reduce(
    (sum, item) => sum + (item.actual ?? 0),
    0
  );

  const forecastRevenue = filteredData.reduce(
    (sum, item) => sum + (item.predicted ?? 0),
    0
  );

  const totalRevenue = historicalRevenue + forecastRevenue;

  const breakdown = categories.map((item) => {
    const amount = revenueData.slice(-Number(period)).reduce(
      (sum, row) => sum + row[item.key],
      0
    );

    return {
      ...item,
      amount,
      share: totalRevenue
        ? Math.round((amount / totalRevenue) * 100)
        : 0
    };
  }).filter((item) => (
    category === "All Equipment" || item.key === category
  ));

  const money = (value) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0
    }).format(value);

  return (
    <FeaturePage
      title="Revenue Prediction"
      description="Track rental revenue and explore expected future earnings."
    >
      <div className="revenue-toolbar">
        <div>
          <label htmlFor="revenue-category">Equipment category</label>
          <select
            id="revenue-category"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
          >
            <option value="All Equipment">All Equipment</option>
            <option value="wheelchair">Wheelchairs</option>
            <option value="oxygen">Oxygen Concentrators</option>
            <option value="bed">Hospital Beds</option>
          </select>
        </div>

        <div>
          <label htmlFor="revenue-period">Reporting period</label>
          <select
            id="revenue-period"
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
          >
            <option value="6">Last 6 months</option>
            <option value="12">Last 12 months</option>
          </select>
        </div>
      </div>

      <div className="revenue-demo-note">
        SAMPLE DATA · Illustrative figures, not actual model predictions
      </div>

      <div className="revenue-kpi-grid">
        <article className="revenue-kpi">
          <span>Historical Revenue</span>
          <strong>{money(historicalRevenue)}</strong>
          <p>Historical portion displayed</p>
        </article>

        <article className="revenue-kpi">
          <span>Forecast Revenue</span>
          <strong>{money(forecastRevenue)}</strong>
          <p>Illustrative forecast portion</p>
        </article>

        <article className="revenue-kpi">
          <span>Total Displayed Revenue</span>
          <strong>{money(totalRevenue)}</strong>
          <p>Historical plus forecast</p>
        </article>
      </div>

      <div className="revenue-panel">
        <div className="chart-title">
          <div>
            <h2>Revenue Trend & Forecast</h2>
            <p>Monthly rental revenue in Indian rupees</p>
          </div>
          <span className="demo-badge">DEMO</span>
        </div>

        <div style={{ width: "100%", height: 330, marginTop: 20 }}>
          <RevenueChart data={filteredData} />
        </div>

        <p className="demo-warning">
          Sample values are used for frontend development. Actual revenue
          and forecasts must come from the project's verified data and
          AIML backend.
        </p>
      </div>

      <div className="revenue-panel revenue-breakdown-panel">
        <div className="chart-title">
          <div>
            <h2>Revenue by Equipment</h2>
            <p>Revenue across the selected reporting period</p>
          </div>
        </div>

        <div className="revenue-breakdown">
          {breakdown.map((item) => (
            <div className="revenue-breakdown-item" key={item.key}>
              <div className="revenue-breakdown-heading">
                <strong>{item.label}</strong>
                <span>{money(item.amount)}</span>
              </div>
              <div className="revenue-track">
                <div
                  style={{
                    width: `${Math.min(item.share, 100)}%`
                  }}
                />
              </div>
              <small>{item.share}% of displayed revenue</small>
            </div>
          ))}
        </div>
      </div>
    </FeaturePage>
  );
}



function Allocation() {
  const [equipment, setEquipment] = React.useState("Oxygen Concentrator");
  const [duration, setDuration] = React.useState("12");
  const [searched, setSearched] = React.useState(false);
  const [error, setError] = React.useState("");

  const equipmentOptions = [
    "Oxygen Concentrator",
    "Wheelchair",
    "Hospital Bed",
    "Patient Monitor",
    "Suction Machine"
  ];

  function handleSubmit(event) {
    event.preventDefault();

    const days = Number(duration);

    if (!Number.isInteger(days) || days < 1 || days > 365) {
      setError("Enter a rental duration between 1 and 365 days.");
      setSearched(false);
      return;
    }

    setError("");
    setSearched(true);
  }

  return (
    <FeaturePage
      title="Smart Equipment Allocation"
      description="Find suitable equipment for a customer rental request."
    >
      <div className="allocation-layout">
        <div className="allocation-form-section">
          <h2>Rental Request</h2>
          <p className="form-description">
            Enter the customer's equipment requirements.
          </p>

          <form onSubmit={handleSubmit} className="allocation-form">
            <label htmlFor="equipment">Requested Equipment</label>
            <select
              id="equipment"
              value={equipment}
              onChange={(event) => {
                setEquipment(event.target.value);
                setSearched(false);
              }}
            >
              {equipmentOptions.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>

            <label htmlFor="duration">Rental Duration (days)</label>
            <input
              id="duration"
              type="number"
              min="1"
              max="365"
              step="1"
              value={duration}
              onChange={(event) => {
                setDuration(event.target.value);
                setSearched(false);
              }}
              required
            />

            {error && <p className="form-error">{error}</p>}

            <button className="allocation-submit" type="submit">
              Find Best Equipment
            </button>
          </form>
        </div>

        <div className="allocation-results">
          <span className="result-label">RECOMMENDATION</span>
          <h2>Equipment Match</h2>

          {!searched ? (
            <div className="empty-result">
              <ClipboardCheck size={32} />
              <p>Submit a rental request to view a demo result.</p>
            </div>
          ) : (
            <div className="recommendation-card">
              <span className="demo-badge">DEMO RESULT</span>
              <h3>{equipment}</h3>
              <p className="unit-id">Example unit: OC-104</p>

              <div className="score-row">
                <span>Illustrative suitability</span>
                <strong>94%</strong>
              </div>

              <div className="score-track">
                <div className="score-fill" />
              </div>

              <div className="recommendation-detail">
                <span>Requested duration</span>
                <strong>{duration} days</strong>
              </div>

              <div className="recommendation-detail">
                <span>Condition</span>
                <strong>Example: Excellent</strong>
              </div>

              <div className="recommendation-detail">
                <span>Maintenance</span>
                <strong>Requires verification</strong>
              </div>

              <p className="demo-warning">
                Illustrative only. This is not a live inventory check or
                an actual AI recommendation. Unit availability and
                suitability must be verified by the backend.
              </p>
            </div>
          )}
        </div>
      </div>
    </FeaturePage>
  );
}


export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route index element={<Overview />} />
          <Route path="demand" element={<Demand />} />
          <Route path="utilisation" element={<Utilisation />} />
          <Route path="revenue" element={<Revenue />} />
          <Route path="allocation" element={<Allocation />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
