// Function to fetch the sales data asynchronously
async function fetchSalesData() {
  try {
    const response = await fetch("/dashboard/sales-data/"); // Make sure this matches your API endpoint
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }
    const data = await response.json(); // Parse the JSON response
    return data;
  } catch (error) {
    console.error("Error fetching sales data:", error);
    return null; // Return null if there was an error
  }
}

// Function to render the chart using Chart.js
async function renderChart() {
  const salesData = await fetchSalesData();

  if (!salesData) return;

  const chartEl = document.getElementById("salesChart");
  if (!chartEl) return;

  const ctx = chartEl.getContext("2d");
  new Chart(ctx, {
    type: "bar",
    data: {
      labels: salesData.years,
      datasets: [
        {
          label: "Total Sales",
          data: salesData.total_sales,
          borderColor: "#d99421",
          backgroundColor: "rgba(217, 148, 33, 0.18)",
          borderRadius: 8,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: {
            display: false,
          },
        },
        y: {
          beginAtZero: true,
          grid: {
            color: "rgba(148, 163, 184, 0.22)",
            drawBorder: false,
          },
          ticks: {
            callback: function (value) {
              return "UGX " + Number(value).toLocaleString();
            },
          },
        },
      },
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              return "UGX " + Number(context.raw || 0).toLocaleString();
            },
          },
        },
      },
    },
  });
}

// Call the function to render the chart when the page loads
renderChart();



