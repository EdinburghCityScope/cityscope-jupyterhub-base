require(["jquery","bootstrap"], function ($) {

    $('#DataUploadSubmit').click( function() {
        var errorStr = '';
        var size;
        var filetype;
		if (typeof FileReader !== 'undefined') { //FileReader is a browser supported feature
            if( typeof document.getElementById('fileInput').files[0] !== 'undefined'){
                var size =  document.getElementById('fileInput').files[0].size;
                var filetype =  $('#fileInput').val().split('.').pop().toLowerCase();
                if (filetype !== 'csv'){
                    errorStr += '<li>Only csv files can be uploaded.</li>';
                }
                if (size > 50000000) {
                    errorStr += '<li>The file you have selected is too large. Max size is 50mb.</li>';
    		    }
            }
            if (!size || !filetype) {
                errorStr += '<li>You need to select a file to upload</li>';
    	    }
            if (errorStr.length > 1) {
                $('#errorBlock').html("<ul class='has-error'> " + errorStr +"</ul>");
                $('#fileUploadDiv').addClass('has-error');
                return false;
            }
		}
	});

	$(".modalPopUp").on("click", function(e){
        $("#modalPanel").modal().load(this.href);
		return false;
    });


});
