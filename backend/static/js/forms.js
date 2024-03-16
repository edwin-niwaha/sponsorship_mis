
document.getElementById('is_sponsored').style.display = 'none'; // Hide textbox initially

document.getElementById('is_sponsored').addEventListener('change', function() {
  if (this.value === 'Yes') {
    document.getElementById('sponsorship_type').style.display = 'none';
  } else {
    document.getElementById('sponsorship_type').style.display = 'block';
  }
});