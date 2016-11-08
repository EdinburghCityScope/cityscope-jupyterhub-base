require(["jquery"], function () {

    $('#DataUploadSubmit').click( function() {
		if (typeof FileReader !== 'undefined') {
            var errorStr = '';

            var size =  document.getElementById('fileInput').files[0].size;
            //console.log('size = ' + size);
            var filetype =  $('#fileInput').val().split('.').pop().toLowerCase();
            //console.log('ext = ' + filetype);

            if (filetype !== 'csv'){
                errorStr += '<li>Only csv files can be uploaded.</li>';
            }
            if (size > 50000000) {
                errorStr += '<li>The file you have selected is too large. Max size is 50mb.</li>';
		    }
            //console.log('errorStr.length = ' + errorStr.length);
		    if (errorStr.length > 1) {
		    	$('#errorBlock').html("<ul class='has-error'> " + errorStr +"</ul>");
		    	$('#fileUploadDiv').addClass('has-error');
		    	return false;
		    }
		}
	});

});
