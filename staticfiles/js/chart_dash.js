// =================================== Sponsorship types ===================================
fetch("/dashboard/sponsorship-chart/")
  .then((response) => response.json())
  .then((data) => {
    const labels = data.map((item) => item.sponsorship_type);
    const values = data.map((item) => item.count);

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
              "#FF6384",
              "#36A2EB",
              "#FFCE56",
              "#4BC0C0",
              "#9966FF",
              "#FF9F40",
              "#FFBF00",
              "#FF6F61",
              "#6B5B95",
              "#F7CAC9",
            ],
            borderColor: [
              "#FF6384",
              "#36A2EB",
              "#FFCE56",
              "#4BC0C0",
              "#9966FF",
              "#FF9F40",
              "#FFBF00",
              "#FF6F61",
              "#6B5B95",
              "#F7CAC9",
            ],
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: "top" },
          tooltip: {
            callbacks: {
              label: (tooltipItem) => {
                const total = values.reduce((a, b) => a + b, 0);
                const percentage = ((tooltipItem.raw / total) * 100).toFixed(2);
                return `${tooltipItem.label}: ${tooltipItem.raw} (${percentage}%)`;
              },
            },
          },
        },
      },
    };

    // Create the pie chart
    new Chart(document.getElementById("sponsorshipChart"), chartConfig);
  })
  .catch((error) => console.error("Error fetching sponsorship data:", error));

// =================================== Birthday Graph ===================================
document.addEventListener("DOMContentLoaded", function () {
  fetch("/dashboard/birthdays_by_month/")
    .then((response) => response.json())
    .then((data) => {
      const ctx = document.getElementById("birthdayChart").getContext("2d");

      // Define an array of colors to use for each bar
      const backgroundColors = [
        "rgba(255, 99, 132, 0.2)",
        "rgba(54, 162, 235, 0.2)",
        "rgba(255, 206, 86, 0.2)",
        "rgba(75, 192, 192, 0.2)",
        "rgba(153, 102, 255, 0.2)",
        "rgba(255, 159, 64, 0.2)",
        // Add more colors if you have more months
      ];

      const borderColors = [
        "rgba(255, 99, 132, 1)",
        "rgba(54, 162, 235, 1)",
        "rgba(255, 206, 86, 1)",
        "rgba(75, 192, 192, 1)",
        "rgba(153, 102, 255, 1)",
        "rgba(255, 159, 64, 1)",
        // Add more colors if you have more months
      ];

      // Ensure there are enough colors for the number of bars
      const numOfBars = data.months.length;
      const effectiveBackgroundColors = backgroundColors.slice(0, numOfBars);
      const effectiveBorderColors = borderColors.slice(0, numOfBars);

      new Chart(ctx, {
        type: "line",
        data: {
          labels: data.months,
          datasets: [
            {
              label: "Number of Birthdays",
              data: data.counts,
              backgroundColor: effectiveBackgroundColors,
              borderColor: effectiveBorderColors,
              borderWidth: 1,
            },
          ],
        },
        options: {
          scales: {
            x: {
              beginAtZero: true,
            },
          },
        },
      });
    });
});

// =================================== Birthday PieChart ===================================
async function fetchData() {
  try {
    const response = await fetch("/dashboard/birthdays_by_month/"); // Replace with the actual URL
    const data = await response.json();
    renderPieChart(data);
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

// Function to render the pie chart
function renderPieChart(data) {
  const ctx = document.getElementById("pieChart").getContext("2d");
  const pieChart = new Chart(ctx, {
    type: "pie",
    data: {
      labels: data.months,
      datasets: [
        {
          label: "Number of Birthdays",
          data: data.counts,
          backgroundColor: [
            "#FF6384",
            "#36A2EB",
            "#FFCE56",
            "#E7E9ED",
            "#4BC0C0",
            "#FF9F40",
            "#FFCD56",
            "#FF4F81",
            "#4B77BE",
            "#F4D03F",
            "#48C9B0",
            "#E74C3C",
          ],
          borderColor: "rgba(0, 0, 0, 0.1)",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: "top",
        },
        datalabels: {
          color: "#fff",
          display: true,
          formatter: function (value, context) {
            return context.label + ": " + value;
          },
          font: {
            weight: "bold",
          },
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              let label = context.label || "";
              if (label) {
                label += ": " + context.raw + " birthdays";
              }
              return label;
            },
          },
        },
      },
    },
  });
}

// Fetch data when the page loads
window.onload = fetchData;

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
            borderColor: "rgba(75, 192, 192, 1)",
            backgroundColor: "rgba(75, 192, 192, 0.2)",
            fill: false,
          },
          {
            label: "Children Registered",
            data: childrenCounts,
            borderColor: "rgba(255, 99, 132, 1)",
            backgroundColor: "rgba(255, 99, 132, 0.2)",
            fill: false,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          x: {
            title: {
              display: true,
              text: "Year",
            },
          },
          y: {
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
          backgroundColor: "rgba(0, 123, 255, 0.2)", // Bootstrap primary color with transparency
          borderColor: "rgba(0, 123, 255, 1)", // Bootstrap primary color
          borderWidth: 2,
          fill: true, // Fill the area under the line
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        x: {
          title: {
            display: true,
            text: "Year",
          },
        },
        y: {
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
          backgroundColor: "rgba(0, 123, 255, 0.2)", // Bootstrap primary color with transparency
          borderColor: "rgba(0, 123, 255, 1)", // Bootstrap primary color
          borderWidth: 2,
          fill: true, // Fill the area under the line
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        x: {
          title: {
            display: true,
            text: "Year",
          },
        },
        y: {
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
          backgroundColor: "rgba(40, 167, 69, 0.2)", // Bootstrap success color with transparency
          borderColor: "rgba(40, 167, 69, 1)", // Bootstrap success color
          borderWidth: 2,
          fill: true, // Fill the area under the line
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        x: {
          title: {
            display: true,
            text: "Year",
          },
        },
        y: {
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
          backgroundColor: "rgba(40, 167, 69, 0.2)", // Bootstrap success color with transparency
          borderColor: "rgba(40, 167, 69, 1)", // Bootstrap success color
          borderWidth: 2,
          fill: true, // Fill the area under the line
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        x: {
          title: {
            display: true,
            text: "Year",
          },
        },
        y: {
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
