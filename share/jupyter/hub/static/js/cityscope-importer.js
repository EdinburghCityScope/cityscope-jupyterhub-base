require(["jquery","jhapi","bootstrap","datatablesbs"], function ($,JHAPI) {
    "use strict";

    var base_url = window.jhdata.base_url;
    var user = window.jhdata.user;
    var api = new JHAPI(base_url);

$(document).ready(function()
{

  $.get("https://api.github.com/search/repositories?q=user:EdinburghCityScope&order=desc")
    .done(function(data){
      console.log("got the data");
      var githubRepositories = [];
    $.each(data.items, function(index){
      if ((data.items[index].name!='cityscope-loopback-docker')&&(data.items[index].name!='edinburghcityscope-utils')&&(data.items[index].name!='cityscope-notebook'))
      {
          githubRepositories.push([data.items[index].description,'<a target="_blank" href="'+data.items[index].html_url+'">View repository details</a>','<input class="btn btn-primary" type="radio" name="repository" value="'+data.items[index].full_name+'"/>']);
      }

    });

    $("#github-repositories").DataTable({
        data: githubRepositories,
        columns: [
          {title : "Repository name"},
          {title : "Futher Details"},
          {title : "Import data"}
        ]
      });

    })
    .error(function(){
      console.error('Error occurred');
      $("#errorMessage").text("An error occurred retrieving dataset information.")
      $("#errorRow").removeClass("hidden");

    });

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

        }
        else if (xhr.status=="204") {
          console.log("api is stopped");

        }
        else if (xhr.status=="404"){
          console.log("api not yet created");

        }
      }
    });

    $('#repository-form').submit(function(event){

      $("#warningMessage").text("Data setup in progress, please wait...");
      $("#warningRow").removeClass("hidden");

      var values={};
      var i=1;
      $('form#repository-form :radio').each(function(){
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
              $("#errorMessage").text("Error encountered setting up data, is your notebook started?");
              $("#errorRow").removeClass("hidden");
            }
        });
      event.preventDefault();
    });

});

});
