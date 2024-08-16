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
        type: "bar",
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

// =================================== Birthday Graph ===================================

// Function to fetch data from the Django view
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
