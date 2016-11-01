// require jQuery
// require jQuery resizable field
// require marked (https://github.com/chjj/marked)
(function($) {
  $.fn.extend({
    markdownPreview: function(options) {
      // generate markdown preview
      var defaults = {tabString: '    '};
      var opts = $.extend(defaults, options);
      var template = ''
        + '<div class="editor-markdown">'
        + '  <div class="editor-markdown-field-container">'
        + '    <p class="editor-markdown-field-title">Markdown</p>'
        + '  </div>'
        + '  <div class="editor-markdown-preview-container">'
        + '    <p class="editor-markdown-preview-title">Preview</p>'
        + '    <div class="editor-markdown-preview vTextField"></div>'
        + '  </div>'
        + '</div>';

      this.each(function() {
        var field = $(this);

        // allow only for textareas and text inputs
        if (!field.is('textarea, input[type=text]')) return;

        var self = $(template);
        self.insertBefore(field);
        self.find('.editor-markdown-field-container').append(field);

        var preview = self.find('.editor-markdown-preview');
        var updateHTML = function() {
          preview.html(marked(field.val()));
        };
        var updateScroll = function() {
          var percent = field.scrollTop() / (field.prop('scrollHeight') - field.height());
          preview.scrollTop((preview.prop('scrollHeight') - preview.height()) * percent);
        };

        if (field.is('input[type=text]')) {
          preview.addClass('editor-markdown-preview-oneline');
        } else {
          // events for textarea
          field.on('scroll', updateScroll);
          // tab (shift+tab) key control
          field.on('keydown', function(e) {
            var keyCode = e.keyCode || e.which;
            if (keyCode == 9) {
              e.preventDefault();
              var value, position, self = $(this);
              var start = this.selectionStart;
              var end = this.selectionEnd;

              // set field value to: text before caret + tabString + text after caret
              if (e.shiftKey) {
                value = self.val().substring(0, start).replace(
                          new RegExp('\x20{1,' + opts.tabString.length + '}$'), ''
                        ) + self.val().substring(end);
                position = (self.val().length-value.length) * -1;
              } else {
                value = self.val().substring(0, start)
                        + opts.tabString
                        + self.val().substring(end);
                position = opts.tabString.length;
              }
              self.val(value);

              // put caret at right position again
              this.selectionStart =
              this.selectionEnd = start + position;
            }
          });
        }

        // events
        field.on('keyup change', function() {
          updateHTML();
          updateScroll();
        });
        // size update
        field.on('mouseup', function() {
          preview.width($(this).width());
          preview.height($(this).height());
        });

        // initial resizing
        field.trigger('mouseup');
        // initial html rendering
        updateHTML();
      });
    }
  });

  $(document).ready(function() {
    $('.editor_markdown').resizableField();
    $('.editor_markdown').markdownPreview();
  });
})(django && django.jQuery ? django.jQuery : jQuery) // django.jQuery also support
