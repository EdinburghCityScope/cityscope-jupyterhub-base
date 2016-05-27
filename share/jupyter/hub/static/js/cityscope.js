require(["jquery","jhapi","bootstrap"], function ($,JHAPI) {
    "use strict";

    var base_url = window.jhdata.base_url;
    var user = window.jhdata.user;
    var api = new JHAPI(base_url);

$(document).ready(function()
{
  //TODO Add refined query which only returns repositories which contain a data.json in the repo
  $.get("https://api.github.com/search/repositories?q=user:EdinburghCityScope&order=desc")
    .done(function(data){
    $.each(data.items, function(index){
      if ((data.items[index].name!='cityscope-loopback-docker')&&(data.items[index].name!='edinburghcityscope-utils'))
      $("#github-repositories tbody").append('<tr><td>'+data.items[index].description+'</td><td><a target="_blank" href="'+data.items[index].html_url+'">View repository details</a></td><td><input type="checkbox" name="'+data.items[index].full_name+'" value="'+data.items[index].clone_url+'"/></td></tr>');
    });

    })
    .error(function(){
      console.error('Error occurred');
      $("#errorMessage").text("An error occurred retrieving dataset information.")
      $("#errorRow").removeClass("hidden");

    });

    console.info(user);

    $("#stop-loopback-button").hide();
    $("#setup-data-button").hide();

    api.get_loopback_status(user,{
      success: function(xhr) {
      
      },
      complete: function(xhr){

        if (xhr.status=="200")
        {
          console.info('status is up');
          $("#stop-loopback-button").show();
          $("#start-loopback-button").hide();
          $("#setup-data-button").show();
        }
      }
    });


    $('#repository-form').submit(function(event){

      $("#warningMessage").text("Data setup in progress, please wait...");
      $("#warningRow").removeClass("hidden");

      var values={};
      var i=1;
      $('form#repository-form :checkbox').each(function(){
        if ($(this).is(':checked'))
        {
          values[this.name]=$(this).val();
        }

      });
      console.info(values);

      api.setup_loopback(user,JSON.stringify(values), {
            success: function (data) {
                console.info('succesfully updated loopback'+JSON.stringify(data));
                $("#warningRow").addClass("hidden");
                $("#successMessage").text(data.message);
                $("#successRow").removeClass("hidden");
            },
            error: function(error) {
              console.info("error encountered"+error);
              $("#warningRow").addClass("hidden");
              $("#errorMessage").text("Error encountered setting up data");
              $("#errorRow").removeClass("hidden");
            }
        });
      event.preventDefault();
    });

     $("#start-loopback-button").click(function () {
       $("#warningRow").removeClass("hidden");
       $("#warningMessage").text("Starting loopback, please wait...");
        api.start_loopback(user, {
          success: function (data) {
              console.info('succesfully started loopback');
              $("#warningRow").addClass("hidden");
              $("#successRow").removeClass("hidden");
              $("#successMessage").text(data.message);
              $("#stop-loopback-button").show();
              $("#start-loopback-button").hide();
              $("#setup-data-button").show();
          }
      });
    });

     $("#stop-loopback-button").click(function () {
               $("#warningRow").removeClass("hidden");
               $("#warningMessage").text("Stopping loopback, please wait...");
        api.stop_loopback(user, {
            success: function () {
                console.info('succesfully stopped loopback');
                $("#warningRow").addClass("hidden");
                $("#successRow").removeClass("hidden");
                $("#successMessage").text("Loopback stopped.");
                $("#stop-loopback-button").hide();
                $("#start-loopback-button").show();
                $("#setup-data-button").hide();
            }
        });
    });

});

});
