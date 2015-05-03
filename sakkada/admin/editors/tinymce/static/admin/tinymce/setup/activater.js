// require jQuery
// require cookies.js (https://github.com/ScottHamper/Cookies)
(function($){
    var filebrowser_url = '/admin/filebrowser/browse/'; // the URL to the Django filebrowser, depends on your URLconf

    // tinyMCE setup
    var tinymce_activater = function () {
        tinyMCE.init({
            // General options
            mode: "specific_textareas",
            editor_selector: "editor_tinymce",
            theme: "advanced",
            plugins: "table,advimage,advlink,preview,paste,fullscreen,visualchars,nonbreaking",
            relative_urls: false,
            height: 350,
            // content_css: '/static/admin/tinymce/setup/content.css',
            // extended_valid_elements: "style",

            // Filebrowser callback
            file_browser_callback: "filebrowser_callback",

            // Theme options
            theme_advanced_buttons1: "bold,italic,underline,strikethrough,sub,sup,blockquote,|,styleselect,formatselect,fontselect,fontsizeselect",
            theme_advanced_buttons2: "justifyleft,justifycenter,justifyright,justifyfull,|,forecolor,backcolor,|,anchor,link,unlink,image,|,undo,redo,pastetext,pasteword,|,removeformat,cleanup,visualchars,|,code,preview,fullscreen",
            theme_advanced_buttons3: "bullist,numlist,|,outdent,indent,|,tablecontrols,|,hr,charmap,nonbreaking,visualaid",
            theme_advanced_buttons4: "",
            theme_advanced_toolbar_location: "top",
            theme_advanced_toolbar_align: "left",
            theme_advanced_statusbar_location: "bottom",
            theme_advanced_resizing: true

            // Drop lists for link/image/media/template dialogs
            // template_external_list_url: "js/template_list.js",
            // external_link_list_url: "js/link_list.js",
            // external_image_list_url: "js/image_list.js",
            // media_external_list_url: "js/media_list.js",
        });
    }

    // filebrowser callback (note: without var, global scope)
    filebrowser_callback = function(field_name, url, type, win) {
        tinyMCE.activeEditor.windowManager.open(
            {width: 900, height: 600, resizable: "yes", scrollbars: "yes",
             file: filebrowser_url + "?pop=2&type=" + type},
            {window: win, input: field_name, editor_id: tinyMCE.selectedInstance.editorId}
        );
        return false;
    }

    $(function() {
        // save editor_ex state in cookies
        var django_admin_editor_tinymce = false;
        var django_admin_editor_tinymce_is_get = false;
        if (false == django_admin_editor_tinymce_is_get) {
            django_admin_editor_tinymce = Cookies.get('django_admin_editor_tinymce') == 'true';
            $(window).unload(function() {
                Cookies.set('django_admin_editor_tinymce', String(django_admin_editor_tinymce), {'path':'/'});
            });
        }
        django_admin_editor_tinymce && tinymce_activater()

        var textarea_class = 'editor_tinymce';
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
            env = $("<div/>").addClass('tinymce_tools');
            env.prepend(
                '<div class="tinymce_tools_bar">'
                + '<a class="tinymce_tools_bar_browse" href="javascript:void(0);">Filemanager</a>'
                + '<input type="checkbox" class="tinymce_checkbox" />'
                + '</div>'
            );
            env.find('input.tinymce_checkbox').prop('checked', django_admin_editor_tinymce);
            env.insertBefore($(this));
            env.append($(this));

            $('a.tinymce_tools_bar_browse', env).click(function() {
                filebrowser_handler();
                return false;
            });

            $('input:checkbox', env).click(function(e) {
                django_admin_editor_tinymce = $(this).prop('checked');
                $('input:checkbox.tinymce_checkbox').prop('checked', django_admin_editor_tinymce);
                tinyMCE.editors.length ? $(tinyMCE.editors).each(function(index, ed){ ed.remove(); })
                                       : tinymce_activater();
            });
        });
    });
})(django.jQuery);
