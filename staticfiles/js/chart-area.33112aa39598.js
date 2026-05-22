// =================================== Monthly sales for the current year ===================================
document.addEventListener("DOMContentLoaded", async function () {
  await fetchData();
});

async function fetchData() {
  try {
    const response = await fetch("/dashboard/monthly_earnings/");
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }
    const data = await response.json();

    renderLineChart(data.labels, data.data);
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

function renderLineChart(labels, data) {
  const chartEl = document.getElementById("myLineChart");
  if (!chartEl) return;

  var ctx = chartEl.getContext("2d");

  new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Monthly Earnings",
          data: data,
          backgroundColor: "rgba(19, 116, 93, 0.14)",
          borderColor: "#13745d",
          borderWidth: 3,
          fill: true,
          pointRadius: 3,
          pointBackgroundColor: "#ffffff",
          pointBorderColor: "#13745d",
          pointHoverRadius: 5,
          pointHoverBackgroundColor: "#13745d",
          pointHoverBorderColor: "#ffffff",
          pointHitRadius: 8,
          pointBorderWidth: 2,
          tension: 0.35,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      layout: {
        padding: {
          left: 4,
          right: 10,
          top: 8,
          bottom: 0,
        },
      },
      scales: {
        x: {
          beginAtZero: true,
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
              return "UGX " + numberFormat(value, 0);
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
            label: function (tooltipItem) {
              return `${tooltipItem.label}: UGX ${numberFormat(tooltipItem.raw, 0)}`;
            },
          },
        },
      },
    },
  });
}

function numberFormat(
  number,
  decimals = 2,
  dec_point = ".",
  thousands_sep = ","
) {
  number = parseFloat(number).toFixed(decimals).toString();
  const [integer, decimal] = number.split(".");
  return (
    integer.replace(/\B(?=(?:\d{3})+(?!\d))/g, thousands_sep) +
    (decimal ? dec_point + decimal : "")
  );
}



