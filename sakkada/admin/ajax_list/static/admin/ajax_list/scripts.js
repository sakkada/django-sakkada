(function ($) {

  // ajax fields get/set values
  var get_ajax_field_value = function(self) {
    var value = undefined;
    if (self.tagName == "INPUT") {
      if (["text", "textarea"].indexOf(self.type) > -1) {
         value = self.value;
      } else if (self.type == "checkbox") {
         value = self.checked || false;
      } else if (self.type == "radio") {
         value = self.querySelector('input[type="radio"]:checked').value;
      }
    } else if (self.tagName == "SELECT") {
      value = self.value;
    }
    return value;
  }

  var set_ajax_field_value = function(self, value) {
    var value = undefined;
    if (self.tagName == "INPUT") {
      if (["text", "textarea"].indexOf(self.type) > -1) {
         self.value = value;
      } else if (self.type == "checkbox") {
         self.checked = value ? true : false;
      } else if (self.type == "radio") {
         self.querySelector('input[value="'+value+'"]').checked = true;
      }
    } else if (self.tagName == "SELECT") {
      self.value = value;
    }
  }

  // OnClick handler to toggle a boolean field via AJAX
  var ajax_field_change_handler = function(self) {
    var item = self.attributes['data-item'].value,
      attr = self.attributes['data-attr'].value,
      value = get_ajax_field_value(self);

    if (value === undefined) {
      alert('Unable to get value of field "' + attr + '". Unsupported field type.');
      return;
    }

    // disable field to prevent multiple requests
    self.disabled = true;

    $.ajax({
      url: ".",
      type: "POST",
      dataType: "json",
      data: {
        'ajax_list': 'ajax_field_change',
        'item': item,
        'attr': attr,
        'value': value,
        'csrfmiddlewaretoken': Cookies.get('csrftoken')
      },
      success: function (data) {
        var error_message = '';
        if (!data) {
          error_message = 'No data received in request.';
        } else if(data.error == undefined) {
          set_ajax_field_value(data.value);
          self.disabled = false;
        } else {
          error_message = data.error
        }
        if (error_message) {
          alert('Unable to update field "' + attr + '": ' + error_message);
        }
      },
      error: function(xhr, status, err) {
        alert('Unable to update field "' + attr + '": ' + xhr.responseText);
      }
    });
  }

  // window onload event
  $(function(){
    // do nothing if not result_list table
    if (!document.getElementById('result_list')) return;

    // ajax fields change value events
    var queryset = document.querySelectorAll('.ajax_field input, .ajax_field select');
    Array.prototype.forEach.call(queryset, function(el, index, collection) {
      el.addEventListener('change', function(event) {
        event.preventDefault();
        ajax_field_change_handler(this);
      });
    });

    // Show/hide ajax fields
    // set ajax_field_title class to thead>th's
    var thead = document.querySelectorAll('#result_list thead tr')[0];
    Array.prototype.forEach.call(
      document.querySelectorAll('#result_list tbody tr')[0].querySelectorAll('.ajax_field'),
      function(el, index, collection) {
        var index = Array.prototype.indexOf.call(el.parentNode.parentNode.childNodes, el.parentNode);
        thead.querySelectorAll('th')[index].classList.add('ajax_field_title');
      }
    );

    var handle_table_cells = function (action){
      var show = action != 'hide';

      Array.prototype.forEach.call(
        document.querySelectorAll('#result_list .ajax_field'),
        function(el, index, collection) {
          el.parentNode.style.display = show ? '' : 'none';
        }
      );

      Array.prototype.forEach.call(
        document.querySelectorAll('#result_list .ajax_field_title'),
        function(el, index, collection) {
          el.style.display = show ? '' : 'none';
        }
      );
    }

    var ajax_list_hide = Cookies.get('ajax_list') == 'hide';
    ajax_list_hide && handle_table_cells('hide')
    $(window).on('unload', function() {
      Cookies.set('ajax_list', ajax_list_hide ? 'hide' : 'show',
            {path: document.location.pathname});
    });

    document.getElementById('ajaxlist-showhide-fields').addEventListener('click', function (event) {
      event.preventDefault();
      if ($('#result_list .ajax_field_title:eq(0):visible').length) {
        ajax_list_hide = true;
        handle_table_cells('hide');
      } else {
        ajax_list_hide = false;
        handle_table_cells('show');
      }
    });

    // attach keydown/keypress events on table lines
    $('body').keydown(function(event) {
      var status = false;
      switch(event.keyCode) {
        case 220:
          if (event.ctrlKey && event.shiftKey) {
            document.getElementById('ajaxlist-showhide-fields').dispatchEvent(new CustomEvent('click'));
          } else {
             status = true;
          }
          break; // \
        default:
          status = true;
          break;
      }
      return status;
    });
  });

})(django.jQuery);
