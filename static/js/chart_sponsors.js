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
          label: "Number of Sponsors Over Time",
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
