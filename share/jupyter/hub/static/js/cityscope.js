require(["jquery","jhapi","bootstrap"], function ($,JHAPI) {
    "use strict";

    var base_url = window.jhdata.base_url;
    var user = window.jhdata.user;
    var api = new JHAPI(base_url);

$(document).ready(function()
{

    $("#stop-loopback-button").hide();
    $("#start-loopback-button").hide();
    $("#stop-mysql-button").hide();
    $("#goto-my-api").hide();
    $("#stop-my-api").hide();
    $("#stop-wordpress-button").hide();
    $("#stop-blog-button").hide();
    $("#start-blog-button").hide();
    $("#setup-data-button").hide();
    $("#start-mysql-button").show();
    $("#start-wordpress-button").show();
    $("#create-loopback-button").show();
    $("#show-api-password").hide();

    $("#stop-my-fieldtrip").hide();
    $("#start-fieldtrip-button").hide();
    $("#goto-my-fieldtrip").hide();
    $("#show-fieldtrip-password").hide();
    $("#create-fieldtrip-button").show();

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

    api.get_blog_status(user,{
      success: function(xhr) {

      },
      error: function(xhr){
        $("#stop-blog-button").hide();
        $("#goto-my-blog").hide();
        $("#create-blog-button").show();
      },
      complete: function(xhr){

        if (xhr.status=="200")
        {
          console.info('blog is up');
          $("#stop-blog-button").show();
          $("#stop-my-blog").show();
          $("#goto-my-blog").show();
          $("#start-blog-button").hide();
          $("#show-blog-password").show();
          $("#create-blog-button").hide();
        }
        else if (xhr.status=="204") {
          console.log("blog is stopped");
          $("#stop-blog-button").hide();
          $("#stop-my-blog").hide();
          $("#goto-my-blog").hide();
          $("#start-blog-button").show();
          $("#show-blog-password").show();
          $("#create-blog-button").hide();
        }
        else if (xhr.status=="404"){
          console.log("blog not yet created");
          $("#stop-blog-button").hide();
          $("#stop-my-blog").hide();
          $("#goto-my-blog").hide();
          $("#start-blog-button").hide();
          $("#show-blog-password").hide();
          $("#create-blog-button").show();
        }
      }
    });

    api.get_fieldtrip_status(user,{
      success: function(xhr) {

      },
      error: function(xhr){
        $("#stop-my-fieldtrip").hide();
        $("#goto-my-fieldtrip").hide();
        $("#create-fieldtrip-button").show();
      },
      complete: function(xhr){

        if (xhr.status=="200")
        {
          console.info('fieldtrip is up');
          $("#stop-my-fieldtrip").show();
          $("#goto-my-fieldtrip").show();
          $("#start-fieldtrip-button").hide();
          $("#show-fieldtrip-password").show();
          $("#create-fieldtrip-button").hide();
        }
        else if (xhr.status=="204") {
          console.log("fieldtrip is stopped");
          $("#stop-my-fieldtrip").hide();
          $("#goto-my-fieldtrip").hide();
          $("#start-fieldtrip-button").show();
          $("#show-fieldtrip-password").show();
          $("#create-fieldtrip-button").hide();
        }
        else if (xhr.status=="404"){
          console.log("fieldtrip not yet created");
          $("#stop-my-fieldtrip").hide();
          $("#goto-my-fieldtrip").hide();
          $("#start-fieldtrip-button").hide();
          $("#show-fieldtrip-password").hide();
          $("#create-fieldtrip-button").show();
        }
      }
    });

     $("#start-loopback-button").click(function () {
       $("#loopbackSuccessMessage").addClass("hidden");
       $("#loopbackWarningMessage").removeClass("hidden");
       $("#loopbackWarningMessage").text("Starting API, please wait...");
        api.start_loopback(user, {
          success: function (data) {
              console.info('succesfully started loopback');
              $("#loopbackWarningMessage").addClass("hidden");
              $("#loopbackSuccessMessage").removeClass("hidden");
              $("#loopbackSuccessMessage").text(data.message);
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
      $("#loopbackWarningMessage").removeClass("hidden");
      $("#loopbackWarningMessage").text("Starting loopback, please wait...");
       api.start_loopback(user, {
         success: function (data) {
             console.info('succesfully started loopback');
             $("#loopbackWarningMessage").addClass("hidden");
             $("#loopbackSuccessMessage").removeClass("hidden");
             $("#loopbackSuccessMessage").text(data.message);
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

   $("#create-blog-button").click(function(){
     $("#blogSuccessMessage").addClass("hidden");
     $("#blogWarningMessage").removeClass("hidden");
     $("#blogWarningMessage").text("Requesting a new blog for you, please wait...");
     console.log("starting mysql");
     api.start_mysql(user, {
       success: function (data) {
           console.info('succesfully started mysql');
           console.log('starting wordpress')
           api.start_wordpress(user, {
             success: function (data) {
                 console.info('succesfully started Wordpress');
                 $("#blogWarningMessage").addClass("hidden");
                 $("#blogSuccessMessage").removeClass("hidden");
                 $("#blogSuccessMessage").text(data.message);
                 $("#stop-my-blog").show();
                 $("#start-blog-button").hide();
                 $("#create-blog-button").hide();
                 $("#goto-my-blog").show();
                 $("#show-blog-password").show();
             }
           });
         }
       });
   });

   $("#start-blog-button").click(function () {
     $("#blogSuccessMessage").addClass("hidden");
     $("#blogWarningMessage").removeClass("hidden");
     $("#blogWarningMessage").text("Starting your Tour Blog, please wait...");
     api.start_mysql(user, {
       success: function (data) {
           console.info('succesfully started mysql');
           console.log('starting wordpress')
           api.start_wordpress(user, {
             success: function (data) {
                 console.info('succesfully started Wordpress');
                 $("#blogWarningMessage").addClass("hidden");
                 $("#blogSuccessMessage").removeClass("hidden");
                 $("#blogSuccessMessage").text(data.message);
                 $("#stop-my-blog").show();
                 $("#start-blog-button").hide();
                 $("#create-blog-button").hide();
                 $("#goto-my-blog").show();
             }
           });
         }
       });
   });

     $("#start-fieldtrip-button").click(function () {
       $("#fieldTripSuccessMessage").addClass("hidden");
       $("#fieldTripWarningMessage").removeClass("hidden");
       $("#fieldTripWarningMessage").text("Starting Fieldtrip, please wait...");
        api.start_fieldtrip(user, {
          success: function (data) {
              console.info('succesfully started fieldtrip');
              $("#fieldTripWarningMessage").addClass("hidden");
              $("#fieldTripSuccessMessage").removeClass("hidden");
              $("#fieldTripSuccessMessage").text(data.message);
              $("#stop-my-fieldtrip").show();
              $("#start-fieldtrip-button").hide();
              $("#create-fieldtrip-button").hide();
              $("#goto-my-fieldtrip").show();
              $("#show-fieldtrip-password").show();
          }
      });
    });

    $("#create-fieldtrip-button").click(function () {
      $("#fieldTripSuccessMessage").addClass("hidden");
      $("#fieldTripWarningMessage").removeClass("hidden");
      $("#fieldTripWarningMessage").text("Starting Fieldtrip, please wait...");
       api.start_fieldtrip(user, {
         success: function (data) {
             console.info('succesfully started fieldtrip');
             $("#fieldTripWarningMessage").addClass("hidden");
             $("#fieldTripSuccessMessage").removeClass("hidden");
             $("#fieldTripSuccessMessage").text(data.message);
             $("#stop-my-fieldtrip").show();
             $("#start-fieldtrip-button").hide();
             $("#create-fieldtrip-button").hide();
             $("#goto-my-fieldtrip").show();
             $("#show-fieldtrip-password").show();
         }
     });
   });


   $("#show-api-password").click(function(){
     api.get_loopback_credential(user,{
       success: function(data){
         $("#apiPasswordModalBody").html(data);
         $('#apiPasswordModal').modal();
       }
     });
     return false;

   });

   $("#show-blog-password").click(function(){
     api.get_blog_credential(user,{
       success: function(data){
         $("#blogPasswordModalBody").html(data);
         $('#blogPasswordModal').modal();
       }
     });
     return false;

   });

   $("#show-fieldtrip-password").click(function(){
     api.get_fieldtrip_credential(user,{
       success: function(data){
         $("#fieldtripPasswordModalBody").html(data);
         $('#fieldtripPasswordModal').modal();
       }
     });
     return false;

   });

     $("#stop-my-api").click(function () {
               $("#loopbackWarningMessage").removeClass("hidden");
               $("#loopbackSuccessMessage").addClass("hidden");
               $("#loopbackWarningMessage").text("Stopping API, please wait...");
        api.stop_loopback(user, {
            success: function () {
                console.info('succesfully stopped loopback');
                $("#loopbackWarningMessage").addClass("hidden");
                $("#loopbackSuccessMessage").removeClass("hidden");
                $("#loopbackSuccessMessage").text("Loopback stopped.");
                $("#stop-loopback-button").hide();
                $("#stop-my-api").hide();
                $("#goto-my-api").hide();
                $("#start-loopback-button").show();
                $("#setup-data-button").hide();
            }
        });
        return false;
    });

     $("#stop-my-fieldtrip").click(function () {
         $("#fieldTripSuccessMessage").addClass("hidden");
         $("#fieldTripWarningMessage").removeClass("hidden");
         $("#fieldTripWarningMessage").text("Stopping Fieldtrip, please wait...");
        api.stop_fieldtrip(user, {
            success: function () {
                console.info('succesfully stopped Fieldtrip');
                $("#fieldTripWarningMessage").addClass("hidden");
                $("#fieldTripSuccessMessage").removeClass("hidden");
                $("#fieldTripSuccessMessage").text("Fieldtrip stopped.");
                $("#stop-my-fieldtrip").hide();
                $("#goto-my-fieldtrip").hide();
                $("#start-fieldtrip-button").show();
            }
        });
        return false;
    });

   $("#stop-my-blog").click(function () {
     $("#blogSuccessMessage").addClass("hidden");
     $("#blogWarningMessage").removeClass("hidden");
     $("#blogWarningMessage").text("Stopping Tour Blog, please wait...");
      api.stop_wordpress(user, {
          success: function () {
              console.info('succesfully stopped Tour Blog');
              $("#blogWarningMessage").addClass("hidden");
              $("#blogSuccessMessage").removeClass("hidden");
              $("#blogSuccessMessage").text("Blog stopped.");
              $("#stop-my-blog").hide();
              $("#start-blog-button").show();
              $("#goto-my-blog").hide();
          }
      });
      return false;
  });



});

});
