// require jQuery
// require jQuery.cookie

$(function() {
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

    textarea_class = 'editor_simple_fb'

    // morph each textarea marked as editor_ex
    $('textarea.' + textarea_class).each(function(){
        var env
        env = $("<div/>").addClass('editor_tools')
        env.insertBefore($(this))
        env.prepend($("<div/>").addClass('editor_tools_bar'))
        env.find('div')
        .prepend($("<a/>").addClass('editor_tools_bar_browse').attr('href', '#').html('filemanager').css('color', '#0a0'))
        .prepend($("<a/>").addClass('editor_tools_bar_resize') .attr('href', '#').html('large'))
        env.append($(this))

        $('a.editor_tools_bar_browse', env).click(function() {
            filebrowser_link()
            return false
        })

        $('a.editor_tools_bar_resize', env).click(function() {
            data = 'large' == $(this).text() ? {name: 'small', size: 450}
                                            : {name: 'large', size: 200}
            $(this).text(data['name'])
            editor_resize($(this).parent().parent(), 'height', data['size'])
            return false
        })
    })
})