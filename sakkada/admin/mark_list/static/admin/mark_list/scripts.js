(function ($) {
  // note: script is a little hacky - it generates and adds style tag to the head,
  //       marks help information tag after change_list paginator tag and highlights
  //       change_list table.tr lines if required.

  // common functions
  var colorValueToClassName = function(value) {
    return 'marks-tr-bg-' + value.replace('#', '');
  }

  // handlers
  var marksInfoHandler = function(e) {
    // show or hide information
    e.preventDefault();

    var infotag = $(this).next(),
        enabled = infotag.data('enabled');

    if (e.type == 'click') {
      infotag.data('enabled', !enabled);
      if (enabled) {
        infotag.removeClass('marks-info-visible');
      } else {
        infotag.addClass('marks-info-visible');
      }
    } else if (!enabled) {
      if (e.type == 'mouseleave') {
        infotag.removeClass('marks-info-visible');
      } else {
        infotag.addClass('marks-info-visible');
      }
    }
  }

  $(function(){
    // do nothing if no one marks span
    if (!$('span.marks').length) return;

    // get marks with (active status and row-on) or with row-off
    var colorized = $('table#result_list tr td span.marks[data-row-color]');

    // colorize tr tags which contains colorized marks
    colorized.each(function(index, elem) {
      $(elem).parents('tr').addClass(colorValueToClassName($(elem).data('rowColor')));
    });

    // style tag in head and help text tag after change_list table
    var helpTag = [],
        helpTemplate = [
          '<p class="help">\n{text}\n</p>',
          '{br}<span style="color: {color}; cursor: pointer;">&#11044;</span> — {title}'
        ],
        styleTag = {'unique': {}, 'result': []},
        styleTemplate = '<style>'
          + '.marks-container { position: relative; }'
          + '.marks-info { display: none; }'
          + '.marks-info.marks-info-visible {'
          + ' display: block;'
          + ' position: absolute;'
          + ' z-index: 9999;'
          + ' background: #ffc;'
          + ' border: 1px #aaa solid;'
          + ' padding: 10px 12px 10px 12px;'
          + ' font-family: monospace;'
          + '}'
          + '{text}'
          + '</style>';

    // get first marks container and fetch all required data
    $('span.marks[data-row-color]').each(function(index, elem) {
      var item = $(elem);

      // add unique class names to style tag
      styleTag.unique[colorValueToClassName(item.data('rowColor'))] = '{ background-color: ' + item.data('rowColor') + '; }';
    });

    $('span.marks:first span.marks-bar span').each(function(index, elem) {
      // add new line to help tag
      var line = helpTemplate[1],
          data = $(elem);
      data = {'color': data.data('on'), 'title': data.attr('title'), 'br': index ? '<br>' : ''};
      for (var key in data) {
        line = line.replace('{' + key + '}', data[key]);
      }
      helpTag.push(line);
    });

    // insert help tag after paginator
    $(helpTemplate[0].replace('{text}', helpTag.join('\n'))).insertAfter('.paginator');

    // append style tag to head
    for (var key in styleTag.unique) {
      styleTag.result.push('.' + key + ' ' + styleTag.unique[key]);
    }
    $(styleTemplate.replace('{text}', styleTag.result.join('\n'))).appendTo('head');

    // info tags processing: map hanlers, add dynamically created class, remove display
    $('.marks-bar').hover(marksInfoHandler, marksInfoHandler).click(marksInfoHandler)
                   .next().addClass('marks-info').css({'display': ''});
  });

})(django.jQuery);
