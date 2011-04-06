//  IE_COMPAT
//  Re-implement some methods IE sadly does not

if (typeof(Array.prototype.indexOf) == 'undefined') {
    // indexOf() function prototype for IE6/7/8 compatibility, taken from
    // JavaScript Standard Library - http://www.devpro.it/JSL/
    Array.prototype.indexOf=function(elm,i) {
        var j=this.length;
        if(!i)i=0;
        if(i>=0){
            while(i<j){if(this[i++]===elm){i=i-1+j;j=i-j;}}
        } else 
            j=this.indexOf(elm,j+i);
        return j!==this.length?j:-1;
    }
}

if (!Array.prototype.filter) {
    Array.prototype.filter = function(fun /*, thisp*/) {
        var len = this.length;
        if (typeof fun != "function")
            throw new TypeError();

        var res = new Array();
        var thisp = arguments[1];
        for (var i = 0; i < len; i++)
            {
                if (i in this)
                    {
                        var val = this[i]; // in case fun mutates this
                        if (fun.call(thisp, val, i, this))
                            res.push(val);
                    }
            }

        return res;
    };
}

//  TOOLBOX
//  Contains universally useful functions

//  Extract an object id (numeric) from a DOM id. Assumes that a "-" is used
//  as delimiter. Returns either the id found or 0 if something went wrong.
//      extract_item_id('foo_bar_baz-327') -> 327

var extract_item_id = function(elem_id) {
    var i = elem_id.indexOf('-')
    if(i >= 0) return parseInt(elem_id.slice(i+1))
    return 0
}

//  Given an html snippet (in text form), parses it to extract the id attribute,
//  then replace the corresponding element in the page with the snippet. The
//  first parameter is ignored (so the signature matches what $.each expects).
//      replace_element(0, '<div id="replace_me">New Stuff!</div>')
var replace_element = function(i, html) {
    var r_id = $(html).attr('id')
    $('#' + r_id).replaceWith(html)
}

// Same as above, but processes an array of html snippets
var replace_elements = function(data) {
    $.each(data, replace_element)
}

// OnClick handler to toggle a boolean field via AJAX
var inplace_toggle_boolean = function(item_id, attr) {
    $.ajax({
        url: ".",
        type: "POST",
        dataType: "json",
        data: { '__cmd': 'toggle_boolean', 'item_id': item_id, 'attr': attr },
        success: replace_elements,
        error: function(xhr, status, err) {
          alert("Unable to toggle " + attr + ": " + xhr.responseText)
        }
    })
    return false
}

// ChangeList keydown handler for navigating in CL
var changelist_itemid = function(elem) {
    return extract_item_id($('span.page_marker', elem).attr('id'))
}

var changelist_tab = function(elem, event, direction) {
    event.preventDefault()
    var ne = ((direction > 0) ? elem.nextAll() : elem.prevAll()).filter(':visible')[0]
    if(ne) {
        elem.attr('tabindex', -1)
        $(ne).attr('tabindex', '0')
        $(ne).focus()
    }
}

var changelist_openclose = function(elem, openclose) {
    var item_id = changelist_itemid(elem)
    var p = page(item_id)
    if(p && ((openclose && !p.open) || (!openclose && p.open))) {
        page_tree_handler(item_id)
    }
}

//  PAGE TOOLBOX
//  All things javascript specific for the classic page change list

//  25b6: black right-pointing triangle, 25bc: black down-pointing triangle,
//  25b7: white right-pointing triangle, 25BD: white down-pointing triangle
var expand_sym = '\u25B7'
var collapse_sym = '\u25BD'
var feincms_page_open_list
var feincms_page_open_list_is_get = false
var page = function(item_id) { return tree_structure[item_id] }
var recolor_lines = function() {
    $('tbody tr').removeClass('row1').removeClass('row2')
    $('tbody tr:visible:even').addClass('row1')
    $('tbody tr:visible:odd').addClass('row2')
}

//  show all immediate children, then open all children that are marked as open
var open_subtree = function(item_id) {
    var p = page(item_id)
    if (p.children.length == 0) return
    p.ptr.html(collapse_sym)
    $.each(p.children, function(i, id) {
        pp = page(id)
        if(pp.ptr) {
            pp.row.show()
            if(pp.open) open_subtree(id)
        }
    })
}

//  hide all descendants
var close_subtree = function(item_id) {
    var p = page(item_id)
    if(!p.id || !p.children || p.children.length == 0)
        return false

    p.ptr.html(expand_sym)
    $.each(p.descendants, function(i, id) {
        var pp = page(id)
        if(pp.ptr) pp.row.hide()
    })
}

//  click handler
var page_tree_handler = function(item_id) {
    var p = page(item_id)

    if(!p.id || !p.children || p.children.length == 0)
        return false

    var open = p.open
    p.open = !open

    if(open) {
        close_subtree(item_id)
        feincms_page_open_list = feincms_page_open_list.filter(function(o) { return o != item_id })
    } else {
        open_subtree(item_id)
        feincms_page_open_list.push(item_id)
    }
    
    // do I really want that?
    recolor_lines()
    return false
}

//  clean out tree_structure: Remove non existant parents, children, descendants
var tree_structure_clean = function() {

    // If a parent filter is present, remove all leaf elements
    // Must come before tree cleansing!
    $(".admin-filter-parent option").each(function(idx, opt) {
        var valstr = $(opt).attr('value').match(/parent__id__exact=(\d+)/)
        if(!valstr) return

        p = page(parseInt(valstr[1]))
        if(!p.children || p.children.length == 0)
           $(opt).replaceWith('')
    })
    
    // START TREE_STRUCTURE_CLEAN
    if (false == feincms_page_open_list_is_get) {
        feincms_page_open_list_is_get = true
        feincms_page_open_list = $.cookie('feincms_page_open_list')
        // keep a list of open pages to save state across reloads
        if (feincms_page_open_list) {
            var lst = feincms_page_open_list.split(',')
            feincms_page_open_list = []
            for(var i=0; i<lst.length; i++)
                feincms_page_open_list.push(parseInt(lst[i]))
        } else
            feincms_page_open_list = []

        $(window).unload(function() {
            $.cookie('feincms_page_open_list', feincms_page_open_list.join(','), {'path':'/'})
        })
    }
    
    // prepare structure, set row and pointer
    for(k in tree_structure) {
        var p = page(k)
        
        // Precompute object links for no object-id lookups later
        m = $('#page_marker-' + k)
        if(m.length) {
            p.ptr = m
            p.ptr.html(empty_sym)
            p.row = m.parents('tr:first')
        } else {
            // row not present in changelist, throw node away
            tree_structure[k] = {}
        }
    }
    
    // clean out tree_structure: Remove non existant parents, children, descendants
    for (k in tree_structure) {
        var p = page(k)
        if(p.parent && !page(p.parent).ptr)
            p.parent = null

        if(p.descendants)
            p.descendants = $.grep(p.descendants, function(o) { return page(o).ptr })

        if(p.children) {
            p.children = $.grep(p.children, function(o) { return page(o).ptr })
            if(p.children.length)
                p.ptr.html(expand_sym)
        }
    }

    //indent nodes
    $('.node_indent').remove()
    for (k in tree_structure) {
        var p = page(k)
        var level = p.level || 0
        if (!p.ptr) continue

        indent = $('<span/>')
        indent.addClass('node_indent').html(Array(level+1).join('.&nbsp;&nbsp;&nbsp;'))
        p.ptr.parent().find('.node_indent').remove() //? is it need
        p.ptr.before(indent)
    }
    
    // mark as open if page not deleted
    for(i in feincms_page_open_list) {
        var p = page(feincms_page_open_list[i])
        if(p) p.open = true
    }
    // END TREE_STRUCTURE_CLEAN
    
    // sort rows by tree_structure_sort
    last = 0
    for(k in tree_structure_sort) {
        k = k*1
        p = page(tree_structure_sort[k])
        if (!p.ptr) continue
        k ? p.row.parent().find('tr:eq('+(last-1)+')').after(p.row)
          : p.row.parent().prepend(p.row)
        last++
    }
    
    // fill root_items and hide all rows
    root_items = []
    for(k in tree_structure) {
        p = page(k)
        if(p.ptr) {
            p.row && p.row.hide() // default hide
            p.parent || root_items.push(p) // Note all root (ie. has no parent) nodes
        }
    }

    // show all roots and open marked as open
    for(i in root_items) {
        p = root_items[i]
        if(p.row)
            p.row.show()
        if(p.open)
            open_subtree(p.id)
    }
    
    // Recolor lines to correctly alternate again
    $('tbody tr').removeClass('row1').removeClass('row2')
    $('table').show()

    // after visible
    $('tr').attr('tabindex', '-1')
    $('tr:eq(1)').attr('tabindex', '0').focus()

    recolor_lines()
}

var close_entire_tree = function() {
    for(k in tree_structure) {
        close_subtree(k)
    }
    feincms_page_open_list = []
    recolor_lines()
}

var open_entire_tree = function() {
    feincms_page_open_list = []
    for(k in tree_structure) {
        if(page(k) && page(k).children) {
            open_subtree(k)
            feincms_page_open_list.push(k)
        }
    }
    recolor_lines()
}

//  Cut/Copy/Paste support
//  FIXME: This changes the site structure and would need to refresh at least the
//  tree_structure (if not more, eg. page filter). Easy way out: reload the page.

var cut_item_pk = null
function cut_item(pk, elem) {
    var row = $(elem.parentNode.parentNode)
    if(row.hasClass('cut')) {
        cut_item_pk = null
        $('a.paste_target').hide()
        row.removeClass('cut')
    } else {
        cut_item_pk = pk
        $('a.paste_target').show()
        $('tr').removeClass('cut')
        row.addClass('cut').find('a.paste_target').hide()
    }
    return false
}

function paste_item(pk, position) {
    if(!cut_item_pk) return false
    $.post('.', {
            '__cmd': 'move_node',
            'position': position,
            'cut_item': cut_item_pk,
            'pasted_on': pk
        }, 
        function(data) {
            var error_message = ''
            if(data.slice(0,2) == 'OK') {
                data = data[2] == '{' && data.slice(-1) == '}' ? data.slice(2) : '{}'
                try { data = $.parseJSON(data) }
                catch(err) { error_message = 'Error: JSON parsing error.' }
                if (!data) { error_message = 'Error: No data received after request.' }
                if (error_message) { alert(error_message); return }
                
                tree_structure = data
                tree_structure_sort = tree_structure.sort
                delete tree_structure.sort
                tree_structure && tree_structure_clean()
            } else {
                alert(data + '\nThis page will reload now.')
                window.location.reload()
            }
        }
    )

    return false
}

$(function(){
    // Show/hide ajax booleans
    var cb_first = $('table#result_list tr:eq(1)').find('td div input:checkbox:eq(0)').parent().parent().prevAll().length
    var cb_count = $('table#result_list tr:eq(1)').find('td div input:checkbox').length
    var tb_cells = $('table#result_list tr').find('> :gt('+(cb_first-1)+'):lt('+(cb_count)+')')
    feincms_page_hide_bools = $.cookie('feincms_page_hide_bools') == 'true'
    feincms_page_hide_bools && tb_cells.hide()
    $(window).unload(function() { $.cookie('feincms_page_hide_bools', feincms_page_hide_bools+'', {'path':'/'}) })
    $('#show_hide_ajax_bools').click(function (){ if ($(tb_cells[0]).css('display') == 'none') { feincms_page_hide_bools = false; tb_cells.show(); } else { feincms_page_hide_bools = true; tb_cells.hide(); } })
})