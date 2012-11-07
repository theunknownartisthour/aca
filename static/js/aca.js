<!-- autosize and autobuttons for comment boxes -->
$(function(){
  $('.comment-text').autosize({append: "\n"});
});
$(function(){ 
  // Place hints in all comment-text input elements with empty title attributes
  $('.comment-text[title!=""]').hint();
});
$(document).ready(function () {
  <!-- set temporary width -->
  var windowWidth = (parseInt($(window).width())) * 0.75;
  $('#loading-message').css({'width':windowWidth});
  <!-- Fits videos in fluid grid -->
  // Target your .container, .wrapper, .post, etc.
  $(".center-stage").fitVids({ customSelector: "object[src^='/']"});
  // If signed in, append a publish comment button when comment text is clicked.
  $('.comment-text').focus(function() {
    var form = $(this).parent();
    if (!form.find('input').length) {
      if ($('#not-signed-in').length) {
        window.location = $('#not-signed-in').attr('href') + '%23' + $(this).attr('id');
      }
      else {
        $(form).append('<div><input class="publish" id="publish-it" type="submit" value="Publish Comment" /></div>');
      }
    }
  });
  $('.comment-text').blur(function() {
    var form = $(this).parent()
    if ($.trim($(this).val()) == "add your comment...") {
        // user did not add comment, remove the div with publish comment button
      $(form.find('div')).remove();
    }
  });
  // History
  // set inital state to accessed page
  var updateNav = function(state){
      // Make clicked menu active
  $('a[href="#'+state+'"]').parent().addClass('active').siblings('.active').removeClass('active');
  }
  var updateMainView = function(state){
      // Make clicked menu active
  console.log('in uMV ', '#' + state);
  $('#' + state + '-div').removeClass('hidden').siblings().addClass('hidden');
//        $('#' + state + '-div').siblings().addClass('hidden');
    // unhide selected sections and hide all others
  };
  if (location.pathname == '/') {
    updateNav('the-archive');
    updateMainView('the-archive');
  }
  if (location.pathname == '/my-articles') {
    updateNav('my-articles');
    updateMainView('my-articles');
    $('#the-archive-div').load('/ #the-archive-div > *');
  }
  if (location.pathname == '/about') {
    updateNav('about');
    updateMainView('about');
  }
  $.History.bind(function(state){
      // Update the current element to indicate which state we are now on
      console.log('Our current state is: ['+state+']');
  });
  $.History.bind('the-archive', function(state){
    updateNav(state);
    updateMainView(state);
    if (!$('#the-archive-div').contents().length) {
      $('#the-archive-div').load('/ #the-archive-div > *');
    }
    $(".center-stage").fitVids({ customSelector: "object[src^='/']"});
    console.log('fitvid was called');
 });
  $.History.bind('my-articles', function(state){
    updateNav(state);
    updateMainView(state);
    if (!$('#my-articles-div').contents().length) {
      $('#my-articles-div').load('my-articles #my-articles-div > *');
    }
  });
  $.History.bind('create-article', function(state){
    updateNav(state);
    updateMainView(state);
    if (!$('#create-article-div').contents().length) {
      $('#create-article-div').load('create-article');
    }
  });
  $.History.bind('about', function(state){
    updateNav(state);
    updateMainView(state);
    if (!$('#about-div').contents().length) {
      $('#about-div').load('about #about-div > *');
    }
  });
  // edit comment
  $('body').on('mouseenter', '.comment', function(){
      var user = $('.signed-in').attr('nickname').split('@')[0];
      var comment_author = $(this).attr('author');
      if (user == comment_author){
        $(this).css( 'cursor', 'pointer' );
      }
  });
  // helps .on submit detect which button was pressed
  $('body').on('click', 'input[type=submit]', function(e) {
        console.log($(this));
        $(this.form).data('clicked', this.value);
  });
  $('body').on('click', '.comment', function(){
      // create and show comment-edit form if comment is by signed in user
      var user = $('.signed-in').attr('nickname').split('@')[0];
      var comment_author = $(this).attr('author');
        console.log('in .comment', $(this));
      if (user == comment_author){
        var $comment_edit = $('.comment-add-' + $(this).attr('article')).clone();
        $comment_edit.attr('class', 'comment-edit');
        $comment_edit.insertAfter($(this));
        $comment_edit.find('div').remove();
        previous_comment = $(this).find('span[class="comment-display"]').text();
        $comment_edit.find('.comment-text').val(previous_comment);
        $comment_edit.find('.comment-text').attr('title', previous_comment);
        $comment_edit.find('.comment-form').attr('comment-id', $(this).attr('comment-id'));
        $comment_edit.find('.comment-form').attr('name', 'comment-edit-form');
        $comment_edit.find('.comment-form').attr('class', 'comment-edit-form');
        $(this).attr('class', 'comment hidden');
        $(this).next().find('textarea').focus();
        $(this).next().find('textarea').click();
      }
  });
  $('body').on('click', '.comment-edit', function(){
      // user has clicked into edit commnet
        console.log('in .comment-edit', $(this).find('input[class="publish"]').length);
      if (!$(this).find('input[class="publish"]').length) {
          $(this).find('.comment-edit-form').append('<div><input class="publish" id="publish-it" name="update" type="submit" value="Update" style="display: inline;" /><input class="publish" name="update" id="delete-it" type="submit" value="Delete" style="display: inline;"/></div>');
       }
  });
  $('body').on('mouseleave', '.comment-edit', function(){
      if ($(this).find('textarea').attr('title') == $(this).find('textarea').val()) {
        $(this).prev().attr('class', 'comment');
        $(this).remove();
      }
  });
  $('body').on('submit', '.comment-form', function(e) {
    var article_id = $(this).attr('article');
    var $textarea = $(this).find('textarea');
    var text = $textarea.val();
    $.ajax ({
        url: "/ArchiveService.post_comment",
        type: "POST",
        data: JSON.stringify({"article_id": article_id, "comment_text": text}),
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        success: function(data) {
            // copy hidden comment row before modifying with new comment
            var $clone = $('#comment-' + article_id).clone();
        console.log('clone= ', $clone);
            $('#comment-table-' + article_id).append($clone);
            // fill in and unhide new comment row
            new_comment_id = 'comment-' + article_id + '-' + data.comment_id
        console.log('new_comment_id= ', new_comment_id);
            $('#comment-' + article_id).attr('id', new_comment_id);
            $('#' + new_comment_id).find('span[class="comment-display"]').text(text);
            $('#' + new_comment_id).find('a[class="comment-user"]').attr(data.user_url);
            $('#' + new_comment_id).find('a[class="comment-user"]').text(data.nickname.split('@')[0]);
            $('#' + new_comment_id).attr('comment-id', data.comment_id);
            $('#' + new_comment_id).attr('author', data.nickname.split('@')[0]);
            $('#' + new_comment_id).attr('class', 'comment');
        }
    });
    // reset comment form
    $textarea.val('');
    $('.comment-text[title!=""]').hint();
     $($(this).find('div')).remove();
    return false;
  });
  $('body').on('submit', '.comment-edit-form', function(e) {
    var article_id = $(this).attr('article');
    var comment_id = $(this).attr('comment-id');
    var $textarea = $(this).find('textarea');
    var text = $textarea.val();
    console.log($(this).data('clicked'), $(this));
    if ($(this).data('clicked') == "Update") {
        console.log($(this).attr('value'));
        $.ajax ({
            url: "/ArchiveService.edit_comment",
            type: "POST",
            data: JSON.stringify({"article_id": article_id, 
                                  "comment_text": text, 
                                  "comment_id": comment_id}),
            dataType: "json",
            contentType: "application/json; charset=utf-8",
            success: function(data) {
                // update and unhide edited comment
                new_comment_id = 'comment-' + article_id + '-' + comment_id;
                $('#' + new_comment_id).find('span[class="comment-display"]').text(text);
                $('#' + new_comment_id).find('span[class="comment-relativetime"]').text('0 minutes ago');
                $('#' + new_comment_id).attr('class', 'comment');
                $('#' + new_comment_id).next().remove();
            }
        });
    }
    if ($(this).data('clicked') == "Delete") {
        console.log('in delete');
        $.ajax ({
            url: "/ArchiveService.delete_comment",
            type: "POST",
            data: JSON.stringify({"article_id": article_id, 
                                  "comment_text": '', 
                                  "comment_id": comment_id}),
            dataType: "json",
            contentType: "application/json; charset=utf-8",
            success: function(data) {
                // update and hide deleted comment row
                deleted_comment_id = 'comment-' + article_id + '-' + comment_id;
                $('#' + deleted_comment_id).attr('class', 'comment deleted');
                $('#' + deleted_comment_id).next().remove();
                
            }
        });
    }
    return false;
  });
});