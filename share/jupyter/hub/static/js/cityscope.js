require(["jquery","jhapi"], function ($,JHAPI) {
    "use strict";

    var base_url = window.jhdata.base_url;
    var user = window.jhdata.user;
    var api = new JHAPI(base_url);

$(document).ready(function()
{
  $.get("https://api.github.com/search/repositories?q=user:EdinburghCityScope&order=desc")
    .done(function(data){
    $.each(data.items, function(index){
      $("#github-repositories tbody").append('<tr><td>'+data.items[index].description+'</td><td><a target="_blank" href="'+data.items[index].html_url+'">View repository details</a></td><td><input type="checkbox" name="'+data.items[index].name+'" value="'+data.items[index].clone_url+'"/></td></tr>');
    });

    })
    .error(function(){
      console.error('Error occurred');
    });

    console.info(user);

    $("#stop-loopback-button").hide();
    
    api.get_loopback_status(user,{
      success: function() {
        console.info('status is up');
        $("#stop-loopback-button").show();
        $("#start-loopback-button").hide();
      }
    });


    $('#repository-form').submit(function(event){
      var values={};
      $('form#repository-form :checkbox').each(function(){
        if ($(this).is(':checked'))
        {
          values[this.name]=$(this).val();
        }

      });
      console.info(values);

      api.setup_loopback(user, {
            success: function () {
                console.info('succesfully updated loopback');
            }
        });
      event.preventDefault();
    });

     $("#start-loopback-button").click(function () {
        api.start_loopback(user, {
          success: function () {
              console.info('succesfully started loopback');
              $("#stop-loopback-button").show();
              $("#start-loopback-button").hide();
          }
      });
    });

     $("#stop-loopback-button").click(function () {
        api.stop_loopback(user, {
            success: function () {
                console.info('succesfully stopped loopback');
                $("#stop-loopback-button").hide();
                $("#start-loopback-button").show();
            }
        });
    });

});

});
