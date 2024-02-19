function printDiv(divName){
    var printContents = document.getElementById(divName).innerHTML;
    var originalContents = document.body.innerHTML;
  
    document.body.innerHTML = printContents;
  
    window.print();
  
    document.body.innerHTML = originalContents;
  
  }
  
  function ExportToExcel(type, fn, dl) {
    var elt = document.getElementById('printMe');
    var wb = XLSX.utils.table_to_book(elt, { sheet: "sheet1" });
    return dl ?
      XLSX.write(wb, { bookType: type, bookSST: true, type: 'base64' }):
      XLSX.writeFile(wb, fn || ('report.' + (type || 'xlsx')));
  }