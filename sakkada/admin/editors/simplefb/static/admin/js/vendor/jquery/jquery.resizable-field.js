/**
 *  Allow size reducing for resizable textarea and save size in localStorage.
 *  Taken from http://jsfiddle.net/nz8ut/ (also allow to make resizable any tag).
 *  Supports django.jQuery noConflict mode.
 *  Also save dimensions in localStorage and allow some customization:
 *    data-dimensions="{width}:{height}" - default dimensions,
 *    data-ukey="{ukey-value}" - save state only for fields with same ukey,
 *    e.g.: data-dimensions="200:300" data-ukey="rich-editor".
 */

(function($) {
  $.fn.extend({
    resizableField: function(options) {
      var resizableHandler = function(e) {
          var self = $(this);
          if (!this.resizableState.active) {
            if (self.width() == this.resizableState.width &&
                self.height() == this.resizableState.height) {
              return;
            }
            this.resizableState.x = e.clientX;
            this.resizableState.y = e.clientY;
            this.resizableState.active = true;
            this.resizableState.changed = true;
            return;
          }

          var w = this.resizableState.width + e.clientX - this.resizableState.x,
              h = this.resizableState.height + e.clientY - this.resizableState.y;
          w < this.resizableState.width && self.width(w);
          h < this.resizableState.height && self.height(h);
      }

      var resizableStop = function(e) {
        this.resizableState.width = $(this).width();
        this.resizableState.height = $(this).height();
        this.resizableState.active = false;
        this.resizableState.changed && localStorage.setItem(
          this.resizableState.uniqueName,
          [this.resizableState.width, this.resizableState.height].join(':')
        );
      }

      this.each(function() {
        // run only once and only for textarea
        if (this.resizableState || this.tagName.toLowerCase() != 'textarea') {
          return;
        }

        var state, self = $(this),
            uniqueName = 'resizable_for_' + (this.dataset['ukey'] || 'default');

        // get dimensions from localStorage or dataset, default none
        state = localStorage.getItem(uniqueName) || this.dataset['dimensions'];
        state = state && state.match(/^\d+:\d+$/)
                ? state.split(':') : [self.width(), self.height()];
        state = {width: state[0]*1, height: state[1]*1,
                 active: false, changed: false, uniqueName: uniqueName};

        // initial state
        state.width == self.width() || self.width(state.width);
        state.height == self.height() || self.height(state.height);

        // events and state linking
        this.resizableState = state;
        self.on('mousemove', resizableHandler);
        self.on('mouseout', resizableStop);
        self.on('mouseup', resizableStop);
      });
    },
  });
})(django && django.jQuery ? django.jQuery : jQuery);
