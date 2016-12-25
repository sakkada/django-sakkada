(function ($) {
  // note: script is a little hacky - it generates and adds style tag to the head,
  //       marks help information tag after change_list paginator tag and highlights
  //       change_list table.tr lines if required.

  // common functions
  var sortByWeightDesc = function(a, b) {
    return ($(b).data('weight')) > ($(a).data('weight')) ? 1 : -1;
  }

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
    var colorized = $('table#result_list tr td span.marks span[data-row-on][data-active], ' +
                      'table#result_list tr td span.marks span[data-row-off]').parents('.marks');

    // colorize tr tags which contains colorized marks
    // (first try - active+rowOn, second - inactive+rowOff)
    colorized.each(function(index, elem) {
      var color, item = $(elem);
      color = item.find('span[data-row-on][data-active]').sort(sortByWeightDesc).toArray().shift() ||
              item.find('span[data-row-off]').not('span[data-active]').sort(sortByWeightDesc).toArray().shift();
      color = color && $(color);
      color = color.data(color.data('active') ? 'rowOn' : 'rowOff');
      // set respective change_list tr class name
      item.parents('tr').addClass(colorValueToClassName(color));
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
    $('span.marks:first span.marks-bar span').each(function(index, elem) {
      var line = helpTemplate[1],
          data = $(elem);

      // add unique class names to style tag
      ['rowOff', 'rowOn'].forEach(function(item, i, arr) {
        item = data.data(item);
        if (item) {
          styleTag.unique[colorValueToClassName(item)] = '{ background-color: ' + item + '; }';
        }
      });

      // add new line to help tag
      data = {'color': data.data('on'), 'title': data.attr('title'),
              'br': index ? '<br>' : ''};
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
