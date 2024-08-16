async function fetchPaymentsData() {
  try {
    const response = await fetch("/dashboard/get_payments_data/");
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
