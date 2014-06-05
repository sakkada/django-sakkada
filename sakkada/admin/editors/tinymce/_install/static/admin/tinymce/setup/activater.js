// require jQuery
// require jQuery.cookie

//tinyMCE setup
var tinymce_activater = function (){
    tinyMCE.init({
        // General options
        mode : "specific_textareas",
        editor_selector : "editor_tinymce",
        theme : "advanced",
        plugins : "table,advimage,advlink,preview,paste,fullscreen,visualchars,nonbreaking",
        relative_urls : false,
        content_css: '/static/admin/tinymce/setup/styles.css',
        height: 350,
        extended_valid_elements: "style",

        // Filebrowser callback
        file_browser_callback: "CustomFileBrowser",

        // Theme options
        theme_advanced_buttons1 : "bold,italic,underline,strikethrough,sub,sup,blockquote,|,styleselect,formatselect,fontselect,fontsizeselect",
        theme_advanced_buttons2 : "justifyleft,justifycenter,justifyright,justifyfull,|,forecolor,backcolor,|,anchor,link,unlink,image,|,undo,redo,pastetext,pasteword,|,removeformat,cleanup,visualchars,|,code,preview,fullscreen",
        theme_advanced_buttons3 : "bullist,numlist,|,outdent,indent,|,tablecontrols,|,hr,charmap,nonbreaking,visualaid",
        theme_advanced_buttons4 : "",
        theme_advanced_toolbar_location : "top",
        theme_advanced_toolbar_align : "left",
        theme_advanced_statusbar_location : "bottom",
        theme_advanced_resizing : true

        // Drop lists for link/image/media/template dialogs
        // template_external_list_url : "js/template_list.js",
        // external_link_list_url : "js/link_list.js",
        // external_image_list_url : "js/image_list.js",
        // media_external_list_url : "js/media_list.js",
    });
}

// filebrowser callback (in global scope)
var CustomFileBrowser = function(field_name, url, type, win) {
    var cmsURL = "/admin/filebrowser/browse/?pop=2";
    cmsURL = cmsURL + "&type=" + type;
    tinyMCE.activeEditor.windowManager.open(
        {file: cmsURL, width: 900, height: 600, resizable: "yes", scrollbars: "yes",},
        {window: win, input: field_name, editor_id: tinyMCE.selectedInstance.editorId}
    );
    return false;
}

$(function() {
    // save editor_ex state
    var django_admin_editor_ex = false
    var django_admin_editor_ex_is_get = false
    if (false == django_admin_editor_ex_is_get) {
        django_admin_editor_ex = $.cookie('django_admin_editor_ex') == 'true'
        $(window).unload(function() { $.cookie('django_admin_editor_ex', django_admin_editor_ex+'', {'path':'/'}) })
    }

    // resize editor field
    var editor_resize = function(container, param, size) {
        object = {}
        object[param] = size
        container.find('textarea.'+textarea_class).animate(object)
    }

    filebrowser_link = function() {
        // the URL to the Django filebrowser, depends on your URLconf
        fb_url = '/admin/filebrowser/browse/'
        dialog = window.open('', 'dialog', "menubar=no,titlebar=no,toolbar=no,resizable=no,width=560,height=300,top=0,left=0")
        dialog.document.write('<html><head><title>Ссылка</title><style>a#link_filebrowser_path { margin: 0 0 0 10px; } #fb_close { margin: 0 0 0 5px; }</style></head><body><fieldset><legend>Ссылка</legend></fieldset></body></html>')
        dialog.document.close()

        dlg = jQuery(dialog.document.body)
        dlg.find('fieldset').append($('<a id="fb_link" title="Filebrowser" href="#">filemanager</a><br>'))
        dlg.find('fieldset').append($('<textarea/>').attr({'id': 'filebrowser_path', 'cols': '52', 'rows': '3'}))
        dlg.find('fieldset').append($('<a id="link_filebrowser_path"><img id="image_filebrowser_path" /></a><br /><span id="help_filebrowser_path"></span>'))
        dlg.find('fieldset').append($('<input id="fb_select" type="submit" value="select text">'))
        dlg.find('fieldset').append($('<input id="fb_close" type="submit" value="close">'))
        dlg.find('#fb_select').click(function() { dlg.find('#filebrowser_path').select(); })
        dlg.find('#fb_close').click(function() { dialog.close(); })
        dlg.find('#fb_link').click(function() { dialog.window.open(fb_url + '?pop=1', 'filebrowser_path', 'height=600,width=900,resizable=yes,scrollbars=yes').focus(); return false; })
        dialog.focus()
    }

    textarea_class = 'editor_tinymce'
    django_admin_editor_ex && tinymce_activater()

    // morph each textarea marked as editor_ex
    $('textarea.' + textarea_class).each(function(){
        var env
        env = $("<div/>").addClass('editor_tools')
        env.insertBefore($(this))
        env.prepend($("<div/>").addClass('editor_tools_bar'))
        env.find('div')
           .prepend($("<input/>").attr('type', 'checkbox').addClass('editor_ex_checkbox').prop('checked', django_admin_editor_ex))
           .prepend($("<a/>").addClass('editor_tools_bar_browse').attr('href', '#').html('filemanager').css('color', '#0a0'))
           .prepend($("<a/>").addClass('editor_tools_bar_resize') .attr('href', '#').html('large'))
        env.append($(this))

        $('a.editor_tools_bar_browse', env).click(function() {
            filebrowser_link()
            return false
        })

        $('a.editor_tools_bar_resize', env).click(function() {
            if (tinyMCE.editors.length) {
                alert('Для изменения размеров редактора tinyMCE\nпотяните за правый нижний угол окна редактора!');
                return false;
            }
            data = 'large' == $(this).text() ? {name: 'small', size: 450}
                                             : {name: 'large', size: 200}
            $(this).text(data['name'])
            editor_resize($(this).parent().parent(), 'height', data['size'])
            return false
        })

        $('input:checkbox', env).bind('click', function() {
            django_admin_editor_ex = $(this).prop('checked')
            $('input:checkbox.editor_ex_checkbox').prop('checked', django_admin_editor_ex)
            tinyMCE.editors.length ? $(tinyMCE.editors).each(function(index, ed){ ed.remove() })
                                   : tinymce_activater()
        })
    })
})
