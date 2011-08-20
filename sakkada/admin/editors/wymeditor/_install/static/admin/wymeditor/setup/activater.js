// require jQuery
// require jQuery.cookie

$(function() {

    // save editor_ex state
    var django_admin_editor_ex = false
    var django_admin_editor_ex_is_get = false
    if (false == django_admin_editor_ex_is_get) {
        django_admin_editor_ex = $.cookie('django_admin_editor_ex') == 'true'
        $(window).unload(function() { $.cookie('django_admin_editor_ex', django_admin_editor_ex+'', {'path':'/'}) })
    }

    // post init wymeditor handler
    var wymeditor_postinit = function(wym){
        // update wymeditor value on textarea blur if toggled
        $(wym._element).blur(function(e){ wym.html($(this).attr('value')) })
        // estetic fix
        $(wym._box).find('.wym_containers h2 span').remove()
        // bind activator event
        $(wym._box).parent().find('input:checkbox').click(function(){
            django_admin_editor_ex = $(this).attr('checked')
            $('input:checkbox.editor_ex_checkbox').attr('checked', django_admin_editor_ex)
            if (django_admin_editor_ex) {
                $('div.wym_box').each(function(){
                    container = $(this).parent()
                    container.find('textarea.' + textarea_class).hide()
                    container.find('.wym_box').show()
                })
            } else {
                $('div.wym_box').each(function(){
                    container = $(this).parent()
                    container.find('textarea.' + textarea_class).show()
                    container.find('.wym_box').hide()
                    wym.update()
                })
            }
        })
    }

    // filebrowser for wymeditor
    var wymeditor_filebrowser = function(wym, wdw) {
        // the URL to the Django filebrowser, depends on your URLconf
        var fb_url = '/admin/filebrowser/browse/';
        var dlg = jQuery(wdw.document.body);

        if (dlg.hasClass('wym_dialog_image')) {
            // this is an image dialog
            dlg.find('.wym_src').attr('id', 'filebrowser').after('<a id="fb_link" title="Filebrowser" href="#">browser</a>');
            dlg.find('fieldset').append('<a id="link_filebrowser"><img id="image_filebrowser" /></a><br /><span id="help_filebrowser"></span>');
            dlg.find('#fb_link').click(function() {
                wdw.open(fb_url + '?pop=1', 'filebrowser', 'height=600,width=900,resizable=yes,scrollbars=yes').focus();
                return false;
            });
        }

        if (dlg.hasClass('wym_dialog_link')) {
            // this is an link dialog
            dlg.find('.wym_href').attr('id', 'filebrowser_href').after('<a id="fb_link_href" title="Filebrowser" href="#">browser</a>');
            dlg.find('fieldset').append('<div style="display: none;"><a id="link_filebrowser_href"><img id="image_filebrowser_href" /></a><span id="help_filebrowser_href"></span></div>');
            dlg.find('#fb_link_href').click(function() {
                wdw.open(fb_url + '?pop=1', 'filebrowser_href', 'height=600,width=900,resizable=yes,scrollbars=yes').focus();
                return false;
            });
        }
    }

    // editor_ex activator
    var textarea_class = 'editor_wymeditor'
    var editor_ex = function(item) {
        $(item).wymeditor({
            stylesheet:     '/media/admin/wymeditor/styles/styles.css',
            skin:           'sakkada',
            lang:           'ru',
            postInit:       wymeditor_postinit,
            postInitDialog: wymeditor_filebrowser
        })
    }

    // wymeditor update requirements
    $('.submit-row input:submit').addClass('wymupdate')

    // resize editor field
    var editor_resize = function(container, param, size) {
        object = {}
        object[param] = size
        visible = container.find('.wym_box').css('display') == 'block'
        if (visible) {
            container.find('iframe').animate(object)
            container.find('textarea.'+textarea_class).css(object)
        } else {
            container.find('iframe').css(object)
            container.find('textarea.'+textarea_class).animate(object)
        }
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

    // morph each textarea marked as editor_ex
    $('textarea.' + textarea_class).each(function(){
        var env
        env = $("<div/>").addClass('editor_tools')
        env.insertBefore($(this))
        env.prepend($("<div/>").addClass('editor_tools_bar'))
        env.find('div')
           .prepend($("<input/>").attr('type', 'checkbox').addClass('editor_ex_checkbox').attr('checked', django_admin_editor_ex))
           .prepend($("<a/>").addClass('editor_tools_bar_browse').attr('href', '#').html('filemanager').css('color', '#0a0'))
           .prepend($("<a/>").addClass('editor_tools_bar_resize') .attr('href', '#').html('large'))
        env.append($(this))

        django_admin_editor_ex && editor_ex(this)

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

        $('input:checkbox', env).one('click', function() {
            if ($('div.wym_box').length) return true
            django_admin_editor_ex = true
            $('input:checkbox.editor_ex_checkbox').attr('checked', django_admin_editor_ex)
            editor_ex($('textarea.'+textarea_class))
        })
    })
})