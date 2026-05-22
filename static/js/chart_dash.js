const dashPalette = {
  green: "#13745d",
  greenSoft: "rgba(19, 116, 93, 0.14)",
  blue: "#2563eb",
  blueSoft: "rgba(37, 99, 235, 0.14)",
  gold: "#d99421",
  goldSoft: "rgba(217, 148, 33, 0.16)",
  coral: "#e05252",
  coralSoft: "rgba(224, 82, 82, 0.14)",
  slate: "#475569",
  grid: "rgba(148, 163, 184, 0.22)",
};

if (window.Chart && Chart.defaults) {
  Chart.defaults.font = Chart.defaults.font || {};
  Chart.defaults.font.family =
    "Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  Chart.defaults.color = "#516173";
}

const modernScaleOptions = {
  grid: {
    color: dashPalette.grid,
    drawBorder: false,
  },
  ticks: {
    padding: 8,
  },
};

// =================================== Sponsorship types ===================================
fetch("/dashboard/sponsorship-chart/")
  .then((response) => response.json())
  .then((data) => {
    const chartElement = document.getElementById("sponsorshipChart");
    if (!chartElement) {
      return;
    }

    const labels = data.map((item) => item.sponsorship_type);
    const values = data.map((item) => item.count);
    const total = values.reduce((a, b) => a + b, 0);

    // Chart configuration
    const chartConfig = {
      type: "pie",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Number of Sponsorships",
            data: values,
            backgroundColor: [
              dashPalette.green,
              dashPalette.blue,
              dashPalette.gold,
              dashPalette.coral,
              "#7c3aed",
              "#0f766e",
              "#f59e0b",
              "#db2777",
              dashPalette.slate,
              "#94a3b8",
            ],
            borderColor: "#ffffff",
            borderWidth: 3,
            hoverOffset: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom" },
          tooltip: {
            callbacks: {
              label: (tooltipItem) => {
                const percentage = total
                  ? ((tooltipItem.raw / total) * 100).toFixed(2)
                  : "0.00";
                return `${tooltipItem.label}: ${tooltipItem.raw} (${percentage}%)`;
              },
            },
          },
        },
      },
    };

    // Create the pie chart
    new Chart(chartElement, chartConfig);
  })
  .catch((error) => console.error("Error fetching sponsorship data:", error));

// =================================== Birthday Graph ===================================
document.addEventListener("DOMContentLoaded", function () {
  fetch("/dashboard/birthdays_by_month/")
    .then((response) => response.json())
    .then((data) => {
      const ctx = document.getElementById("birthdayChart").getContext("2d");

      new Chart(ctx, {
        type: "line",
        data: {
          labels: data.months,
          datasets: [
            {
              label: "Number of Birthdays",
              data: data.counts,
              backgroundColor: dashPalette.goldSoft,
              borderColor: dashPalette.gold,
              borderWidth: 3,
              pointBackgroundColor: "#ffffff",
              pointBorderColor: dashPalette.gold,
              pointRadius: 3,
              tension: 0.35,
              fill: true,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              ...modernScaleOptions,
            },
            y: {
              ...modernScaleOptions,
              beginAtZero: true,
            },
          },
          plugins: {
            legend: { display: false },
          },
        },
      });
    });
});

// =================================== Sponsors against children ===================================
fetch("/dashboard/get_combined_data/")
  .then((response) => {
    if (response.ok) {
      return response.json();
    } else {
      // Handle different HTTP error statuses
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
  })
  .then((data) => {
    // Extract years and sort them
    const allYears = Object.keys(data.sponsors).concat(
      Object.keys(data.children)
    );
    const uniqueYears = [...new Set(allYears)].sort();

    // Filter years to start from 2013
    const startYear = 2013;
    const years = uniqueYears.filter((year) => year >= startYear);

    // Create objects with default values of 0 for missing years
    const sponsorsData = years.reduce((acc, year) => {
      acc[year] = data.sponsors[year] || 0;
      return acc;
    }, {});

    const childrenData = years.reduce((acc, year) => {
      acc[year] = data.children[year] || 0;
      return acc;
    }, {});

    // Map the years to their respective counts
    const sponsorsCounts = years.map((year) => sponsorsData[year]);
    const childrenCounts = years.map((year) => childrenData[year]);

    const ctx = document.getElementById("dataChart").getContext("2d");
    new Chart(ctx, {
      type: "line",
      data: {
        labels: years,
        datasets: [
          {
            label: "Sponsors Registered",
            data: sponsorsCounts,
            borderColor: dashPalette.green,
            backgroundColor: dashPalette.greenSoft,
            borderWidth: 3,
            tension: 0.35,
            fill: true,
          },
          {
            label: "Children Registered",
            data: childrenCounts,
            borderColor: dashPalette.blue,
            backgroundColor: dashPalette.blueSoft,
            borderWidth: 3,
            tension: 0.35,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            ...modernScaleOptions,
            title: {
              display: true,
              text: "Year",
            },
          },
          y: {
            ...modernScaleOptions,
            title: {
              display: true,
              text: "Count",
            },
          },
        },
      },
    });
  })
  .catch((error) => {
    console.error("Error fetching data:", error);
    document.getElementById(
      "errorDisplay"
    ).innerText = `Error: ${error.message}`;
  });

// =================================== All Sponsors ===================================
async function fetchSponsorsData() {
  try {
    const response = await fetch("/dashboard/get_sponsors_data/");
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    renderChart(data);
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

function renderChart(data) {
  const years = data.map((item) => item.year);
  const counts = data.map((item) => item.count);

  const ctx = document.getElementById("sponsorsChart").getContext("2d");
  new Chart(ctx, {
    type: "line",
    data: {
      labels: years,
      datasets: [
        {
          label: "Number of Sponsors",
          data: counts,
          backgroundColor: dashPalette.greenSoft,
          borderColor: dashPalette.green,
          borderWidth: 3,
          tension: 0.35,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          ...modernScaleOptions,
          title: {
            display: true,
            text: "Year",
          },
        },
        y: {
          ...modernScaleOptions,
          title: {
            display: true,
            text: "Number of Sponsors",
          },
          beginAtZero: true,
        },
      },
      plugins: {
        legend: {
          display: true,
          position: "top",
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              return `${context.dataset.label}: ${context.raw}`;
            },
          },
        },
      },
    },
  });
}

// Call the function to fetch data and render the chart
fetchSponsorsData();

// =================================== All Children ===================================
async function fetchChildrenData() {
  try {
    const response = await fetch("/dashboard/get_children_data/");
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    renderChildrenChart(data);
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

function renderChildrenChart(data) {
  const years = data.map((item) => item.year);
  const counts = data.map((item) => item.count);

  const ctx = document.getElementById("childrenChart").getContext("2d");
  new Chart(ctx, {
    type: "line",
    data: {
      labels: years,
      datasets: [
        {
          label: "Number of Children",
          data: counts,
          backgroundColor: dashPalette.blueSoft,
          borderColor: dashPalette.blue,
          borderWidth: 3,
          tension: 0.35,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          ...modernScaleOptions,
          title: {
            display: true,
            text: "Year",
          },
        },
        y: {
          ...modernScaleOptions,
          title: {
            display: true,
            text: "Number of Children",
          },
          beginAtZero: true,
        },
      },
      plugins: {
        legend: {
          display: true,
          position: "top",
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              return `${context.dataset.label}: ${context.raw}`;
            },
          },
        },
      },
    },
  });
}

// Call the function to fetch data and render the chart
fetchChildrenData();

// =================================== Sponsor payments - children ===================================
async function fetchPaymentsData() {
  try {
    const response = await fetch("/dashboard/get_payments_children/");
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    renderPaymentsChart(data);
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

function renderPaymentsChart(data) {
  const years = data.map((item) => item.year);
  const totalAmounts = data.map((item) => parseFloat(item.total_amount));

  const ctx = document.getElementById("paymentsChart").getContext("2d");
  new Chart(ctx, {
    type: "bar",
    data: {
      labels: years,
      datasets: [
        {
          label: "Amount Collected",
          data: totalAmounts,
          backgroundColor: dashPalette.greenSoft,
          borderColor: dashPalette.green,
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
          ...modernScaleOptions,
          title: {
            display: true,
            text: "Year",
          },
        },
        y: {
          ...modernScaleOptions,
          title: {
            display: true,
            text: "Total Amount Collected (UGX)",
          },
          beginAtZero: true,
        },
      },
      plugins: {
        legend: {
          display: false, // Hide legend if not needed
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              return `Amount: UGX ${context.raw.toLocaleString()}`; // Display total amount
            },
          },
        },
      },
    },
  });
}

// Call the function to fetch data and render the chart
fetchPaymentsData();

// =================================== Sponsor payments - staff ===================================

async function fetchPaymentsStaff() {
  try {
    const response = await fetch("/dashboard/get_payments_staff/");
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    renderStaffPaymentsChart(data);
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

function renderStaffPaymentsChart(data) {
  const years = data.map((item) => item.year);
  const totalAmounts = data.map((item) => parseFloat(item.total_amount));

  const ctx = document.getElementById("StaffpaymentsChart").getContext("2d");
  new Chart(ctx, {
    type: "bar",
    data: {
      labels: years,
      datasets: [
        {
          label: "Amount Collected",
          data: totalAmounts,
          backgroundColor: dashPalette.goldSoft,
          borderColor: dashPalette.gold,
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
          ...modernScaleOptions,
          title: {
            display: true,
            text: "Year",
          },
        },
        y: {
          ...modernScaleOptions,
          title: {
            display: true,
            text: "Total Amount Collected (UGX)",
          },
          beginAtZero: true,
        },
      },
      plugins: {
        legend: {
          display: false, // Hide legend if not needed
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              return `Amount: UGX ${context.raw.toLocaleString()}`; // Display total amount
            },
          },
        },
      },
    },
  });
}

// Call the function to fetch data and render the chart
fetchPaymentsStaff();
