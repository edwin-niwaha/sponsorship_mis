function validateForm() {
  var selectedChild = document.getElementById("dropdown").value;

  if (selectedChild === "") {
    alert("Please select a child!");
    return false;
  }

  return true;
}

function validateSPForm() {
  var selectedSponsor = document.getElementById("sp_dropdown").value;

  if (selectedSponsor === "") {
    alert("Please select a Sponsor!");
    return false; // Prevent form submission
  }

  return true; // Allow form submission
}

function validateSTForm() {
  var selectedStaff = document.getElementById("st_dropdown").value;

  if (selectedStaff === "") {
    alert("Please select a Staff!");
    return false; // Prevent form submission
  }

  return true; // Allow form submission
}
