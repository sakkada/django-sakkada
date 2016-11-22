// require jQuery
// require jQuery resizable field
// require jQuery markdown field
(function($) {
  $(document).ready(function() {
    $('.editor_markdown').resizableField();
    $('.editor_markdown').markdownPreview();
  });
})(django && django.jQuery ? django.jQuery : jQuery); // django.jQuery also support
