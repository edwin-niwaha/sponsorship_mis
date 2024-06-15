function validateForm() {
    var selectedChild = document.getElementById("dropdown").value;
    // var selectedSponsor = document.getElementById("sponsor_dropdown").value;

    // if (selectedSponsor === "") {
    //     alert("Please select a Sponsor!");
    //     return false;
    // }

    if (selectedChild === "") {
        alert("Please select a child!");
        return false;
    }

    return true;
}
