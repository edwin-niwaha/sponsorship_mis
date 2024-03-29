    function validateForm() {
        var selectedChild = document.getElementById("dropdown").value;
        if (selectedChild == "") {
            alert("Please select a child!");
            return false;
        }
        return true;
    }
