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
    const years = Object.keys(data.sponsors);
    const sponsorsCounts = years.map((year) => data.sponsors[year] || 0);
    const childrenCounts = years.map((year) => data.children[year] || 0);

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
