(function($){
    $(function() {
        var textarea_class = 'editor_simple_fb'
        var filebrowser_url = '/admin/filebrowser/browse/'; // the URL to the Django filebrowser, depends on your URLconf
        var filebrowser_handler = function() {
            var dialog, dlg;
            dialog = window.open('', 'dialog', "menubar=no,titlebar=no,toolbar=no,resizable=no,width=600,height=300");
            dialog.document.write('<html><head></head><body></body></html>');
            dialog.document.close();

            var head = ''
                + '<title>Filebrowser link</title>'
                + '<style>'
                + '    body { font-family: sans-serif; font-size: 14px; }'
                + '    #filebrowser_wrapper { margin: 5px 0 0 0; }'
                + '    #filebrowser_path { width: 480px; margin: 0 0 6px 0; }'
                + '    #preview_filebrowser_path { float: right; display: none; }'
                + '    #filebrowser_close { margin: 0 0 0 5px; }'
                + '</style>';

            var body= ''
                + '<fieldset>'
                + '    <legend>Filebrowser link</legend>'
                + '    <a id="filebrowser_link" title="Filebrowser" href="javascript:void(0);">Open filebrowser</a>'
                + '    <div id="filebrowser_wrapper">'
                + '        <span id="preview_filebrowser_path">'
                + '            <a id="previewlink_filebrowser_path"><img id="previewimage_filebrowser_path" /></a>'
                + '        </span>'
                + '        <textarea id="filebrowser_path" rows="3"></textarea>'
                + '        <input id="filebrowser_text_select" type="submit" value="select text">'
                + '        <input id="filebrowser_close" type="submit" value="close">'
                + '    </div>'
                + '</fieldset>';

            dlg = $(dialog.document);
            dlg.find('head').append(head);
            dlg.find('body').append(body);

            dlg.find('#filebrowser_link').click(function() {
                dialog.window.open(filebrowser_url + '?pop=1&geturl=1', 'filebrowser_path',
                                   'height=600,width=900,resizable=yes,scrollbars=yes').focus();
                return false;
            })
            dlg.find('#filebrowser_text_select').click(function() { dlg.find('#filebrowser_path').select(); });
            dlg.find('#filebrowser_close').click(function() { dialog.close(); });

            dialog.focus();
        }

        // Update each textarea marked as textarea_class
        $('textarea.' + textarea_class).each(function(){
            var env;
            env = $("<div/>").addClass('simple_fb_tools');
            env.prepend(
                '<div class="simple_fb_tools_bar">'
                + '<a class="simple_fb_tools_bar_browse" href="javascript:void(0);">Filemanager</a>'
                + '</div>'
            );
            env.insertBefore($(this));
            env.append($(this));

            $('a.simple_fb_tools_bar_browse', env).click(function() {
                filebrowser_handler();
                return false;
            });
        });
    });
})(django.jQuery);
