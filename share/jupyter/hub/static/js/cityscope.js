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
      if ((data.items[index].name!='cityscope-loopback-docker')&&(data.items[index].name!='edinburghcityscope-utils')&&(data.items[index].name!='cityscope-notebook'))
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
    $("#start-loopback-button").hide();
    $("#stop-mysql-button").hide();
    $("#goto-my-api").hide();
    $("#stop-my-api").hide();
    $("#stop-wordpress-button").hide();
    $("#setup-data-button").hide();
    $("#start-mysql-button").show();
    $("#start-wordpress-button").show();
    $("#create-loopback-button").show();
    $("#show-api-password").hide();

    api.get_loopback_status(user,{
      success: function(xhr) {

      },
      error: function(xhr){
        $("#stop-loopback-button").hide();
        $("#goto-my-api").hide();
        $("#create-loopback-button").show();
      },
      complete: function(xhr){

        if (xhr.status=="200")
        {
          console.info('api is up');
          $("#stop-loopback-button").show();
          $("#stop-my-api").show();
          $("#goto-my-api").show();
          $("#start-loopback-button").hide();
          $("#setup-data-button").show();
          $("#show-api-password").show();
          $("#create-loopback-button").hide();
        }
        else if (xhr.status=="204") {
          console.log("api is stopped");
          $("#stop-loopback-button").hide();
          $("#stop-my-api").hide();
          $("#goto-my-api").hide();
          $("#start-loopback-button").show();
          $("#setup-data-button").hide();
          $("#show-api-password").show();
          $("#create-loopback-button").hide();
        }
        else if (xhr.status=="404"){
          console.log("api not yet created");
          $("#stop-loopback-button").hide();
          $("#stop-my-api").hide();
          $("#goto-my-api").hide();
          $("#start-loopback-button").hide();
          $("#setup-data-button").hide();
          $("#show-api-password").hide();
          $("#create-loopback-button").show();
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
              $("#stop-my-api").show();
              $("#start-loopback-button").hide();
              $("#create-loopback-button").hide();
              $("#goto-my-api").show();
              $("#setup-data-button").show();
              $("#show-api-password").show();
          }
      });
    });

    $("#create-loopback-button").click(function () {
      $("#warningRow").removeClass("hidden");
      $("#warningMessage").text("Starting loopback, please wait...");
       api.start_loopback(user, {
         success: function (data) {
             console.info('succesfully started loopback');
             $("#warningRow").addClass("hidden");
             $("#successRow").removeClass("hidden");
             $("#successMessage").text(data.message);
             $("#stop-loopback-button").show();
             $("#stop-my-api").show();
             $("#start-loopback-button").hide();
             $("#create-loopback-button").hide();
             $("#goto-my-api").show();
             $("#setup-data-button").show();
             $("#show-api-password").show();
         }
     });
   });

    $("#start-mysql-button").click(function () {
      $("#warningRow").removeClass("hidden");
      $("#warningMessage").text("Starting mysql, please wait...");
       api.start_mysql(user, {
         success: function (data) {
             console.info('succesfully started mysql');
             $("#warningRow").addClass("hidden");
             $("#successRow").removeClass("hidden");
             $("#successMessage").text(data.message);
             $("#stop-mysql-button").show();
             $("#start-mysql-button").hide();

         }
     });
   });

   $("#start-wordpress-button").click(function () {
     $("#warningRow").removeClass("hidden");
     $("#warningMessage").text("Starting Wordpress, please wait...");
      api.start_wordpress(user, {
        success: function (data) {
            console.info('succesfully started Wordpress');
            $("#warningRow").addClass("hidden");
            $("#successRow").removeClass("hidden");
            $("#successMessage").text(data.message);
            $("#stop-wordpress-button").show();
            $("#start-wordpress-button").hide();

        }
    });
   });

   $("#show-api-password").click(function(){
     api.get_loopback_credential(user,{
       success: function(data){
         console.log(data);
         $("#apiPasswordModalBody").html(data);
         $('#apiPasswordModal').modal();
       }
     });

   });


     $("#stop-my-api").click(function () {
               $("#warningRow").removeClass("hidden");
               $("#warningMessage").text("Stopping loopback, please wait...");
        api.stop_loopback(user, {
            success: function () {
                console.info('succesfully stopped loopback');
                $("#warningRow").addClass("hidden");
                $("#successRow").removeClass("hidden");
                $("#successMessage").text("Loopback stopped.");
                $("#stop-loopback-button").hide();
                $("#stop-my-api").hide();
                $("#goto-my-api").hide();
                $("#start-loopback-button").show();
                $("#setup-data-button").hide();
            }
        });
    });

    $("#stop-mysql-button").click(function () {
              $("#warningRow").removeClass("hidden");
              $("#warningMessage").text("Stopping mysql, please wait...");
       api.stop_mysql(user, {
           success: function () {
               console.info('succesfully stopped mysql');
               $("#warningRow").addClass("hidden");
               $("#successRow").removeClass("hidden");
               $("#successMessage").text("MySQL stopped.");
               $("#stop-mysql-button").hide();
               $("#start-mysql-button").show();

           }
       });
   });

   $("#stop-wordpress-button").click(function () {
             $("#warningRow").removeClass("hidden");
             $("#warningMessage").text("Stopping Wordpress, please wait...");
      api.stop_wordpress(user, {
          success: function () {
              console.info('succesfully stopped Wordpress');
              $("#warningRow").addClass("hidden");
              $("#successRow").removeClass("hidden");
              $("#successMessage").text("Wordpress stopped.");
              $("#stop-wordpress-button").hide();
              $("#start-wordpress-button").show();

          }
      });
  });


});

});
