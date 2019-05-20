(function ($) {
    // recolor table lines
    var recolor_lines = function() {
        $('#result_list tbody tr').removeClass('row1').removeClass('row2');
        $('#result_list tbody tr:visible:even').addClass('row1');
        $('#result_list tbody tr:visible:odd').addClass('row2');
    }

    // get node from tree_structure by id
    var get_node = function(item_id) {
        return tree_list.tree_structure.nodes[item_id];
    }

    // get ancestor tag by tag name
    var get_parent_by_tag_name = function (marker, tagName) {
        while (true) {
            marker = marker.parentElement;
            if (!marker || marker.tagName == tagName) break;
        }
        return marker;
    }

    // show all immediate children, then open all children that are marked as open
    var open_subtree = function(item_id) {
        // vanilla js for speedup
        var node = get_node(item_id);
        if (!node || node.children.length == 0) return;
        node.ptr.classList.remove(tree_list.expand_class);
        node.ptr.classList.add(tree_list.collapse_class);
        node.open = true;

        Array.prototype.forEach.call(node.children, function(el, index, collection) {
            var node = get_node(el);
            if (node) {
                node.row.style.display = '';
                node.open && open_subtree(el);
            }
        });
    }

    // hide all descendants
    var close_subtree = function(item_id) {
        // vanilla js for speedup
        var node = get_node(item_id);
        if (!node || node.children.length == 0) return;
        node.ptr.classList.remove(tree_list.collapse_class);
        node.ptr.classList.add(tree_list.expand_class);
        node.open = false;

        Array.prototype.forEach.call(node.descendants, function(el, index, collection) {
            var node = get_node(el);
            if (node) {
                node.row.style.display = 'none';
            }
        })
    }

    // click handler (open/close subtree)
    var openclose_item = function(item_id) {
        var node = get_node(item_id);
        if (!node || node.children.length == 0) return;

        if (node.open) {
            close_subtree(item_id);
            tree_list.tree_state = tree_list.tree_state.filter(function(i) { return i != item_id; });
        } else {
            open_subtree(item_id);
            tree_list.tree_state.push(item_id);
        }
        recolor_lines();
    }

    // open all nodes
    var open_entire_tree = function() {
        tree_list.tree_state = [];
        var node;
        for (var i in tree_list.tree_structure.nodes) {
            node = get_node(i);
            if (node && node.children.length) {
                open_subtree(i);
                tree_list.tree_state.push(i);
            }
        }
        recolor_lines();
    }

    // close all nodes
    var close_entire_tree = function() {
        for (var i in tree_list.tree_structure.nodes) {
            node = get_node(i);
            if (node && node.children.length) {
                close_subtree(i);
            }
        }
        tree_list.tree_state = [];
        recolor_lines();
    }

    // prepare tree_structure on-init/after-response
    var tree_structure_clean = function(initial) {
        initial = initial === true ? true : false;

        // prepare structure: set row and pointer (marker) variables
        //                    if it exists else set node value to null
        for(var i in tree_list.tree_structure.nodes) {
            var node = tree_list.tree_structure.nodes[i];
            var marker = document.getElementById('tree_list_node_marker-' + i);
            if(marker) {
                node.ptr = marker;
                node.row = get_parent_by_tag_name(marker, 'TR') || marker;
            } else {
                tree_list.tree_structure.nodes[i] = null;
            }
        }

        if (!initial) {
            // restore initial state
            for (var i in tree_list.tree_structure.nodes) {
                var node = get_node(i);
                if (!node) continue;

                // restore marker class
                node.ptr.classList.remove(tree_list.expand_class);
                node.ptr.classList.remove(tree_list.collapse_class);
                node.ptr.classList.add(tree_list.empty_class);

                // indent nodes
                var indent = $(node.ptr).prev()[0];
                indent.innerHTML = Array(node.level+1).join('.&nbsp;&nbsp;&nbsp;');
            }

            // order rows by tree_structure.order
            var last = 0, node = null,
                result_list = document.querySelector('#result_list tbody');
            for (var i in tree_list.tree_structure.order) {
                node = get_node(tree_list.tree_structure.order[i]);
                if (!node) continue;
                result_list.insertBefore(node.row, result_list.getElementsByTagName('tr')[last]);
                last++;
            }
        } else {
            // get opened nodes list from cookies (once per request)
            tree_list.tree_state = Cookies.get('tree_list');
            if (tree_list.tree_state) {
                tree_list.tree_state = tree_list.tree_state.split('-');
                tree_list.tree_state.forEach(function(el, i){ this[i] = parseInt(el) },
                                             tree_list.tree_state);
            } else {
                tree_list.tree_state = [];
            }

            $(window).on('unload', function() {
                // save a list of open nodes state across reloads
                Cookies.set('tree_list', tree_list.tree_state.join('-'),
                            {path: document.location.pathname});
            })
        }

        // clean out tree_structure: remove non existant parents, children,
        //                           descendants; update markers
        for (var i in tree_list.tree_structure.nodes) {
            var node = get_node(i);
            if (!node) continue;

            var grepfunc = function(k) { var node = get_node(k); return node && node.ptr; }

            if (node.parent && !get_node(node.parent))
                node.parent = null;

            if (node.descendants)
                node.descendants = $.grep(node.descendants, grepfunc);

            if (node.children) {
                node.children = $.grep(node.children, grepfunc);
                if (node.children.length) {
                    node.ptr.classList.remove(tree_list.empty_class);
                    node.ptr.classList.add(tree_list.expand_class);
                }
            }
        }

        // mark nodes from tree_state as open if it not deleted
        for (var i in tree_list.tree_state) {
            var node = get_node(tree_list.tree_state[i]);
            if (node) {
                node.open = true;
            }
        }

        // get root_items and hide all rows
        var root_items = [];
        for (var i in tree_list.tree_structure.nodes) {
            var node = get_node(i);
            if (node) {
                node.row && (node.row.style.display = 'none'); // hide by default
                node.parent || root_items.push(node);
            }
        }

        // show all roots and open marked as open
        for (var i in root_items) {
            node = root_items[i];
            node.row.style.display = '';
            node.open && open_subtree(node.id);
        }

        recolor_lines()
    }

    // ChangeList keydown handlers for navigating in CL
    var changelist_itemid = function(elem) {
        return $('span.tree_list_node_marker', elem).attr('data-item');
    }

    var changelist_tab = function(elem, event, direction, only_roots) {
        event.preventDefault();
        (direction > 0 ? elem.nextAll() : elem.prevAll()).filter(function(index){
            return only_roots ? $(this).find('span.tree_list_node_marker[level=0]').length > 0 : true;
        }).filter(':visible:eq(0)').focus();
    }

    var changelist_openclose = function(elem, openclose) {
        var item_id = changelist_itemid(elem),
            node = get_node(item_id);
        if (node && ((openclose && !node.open) || (!openclose && node.open))) {
            openclose_item(item_id);
        }
    }

    var changelist_cutitem = function(tr) {
        var icut = tr.getElementsByClassName('tree_list_cut_item')[0];
        cut_item(icut.attributes['data-item'].value, icut);
    }

    var changelist_pasteitem = function(tr, position) {
        var target = $(tr).find('.tree_list_paste_target[data-position=' + position + ']:visible');
        if (!cut_item_pk || !target.length) return;
        paste_item(target[0].attributes['data-item'].value,
                   target[0].attributes['data-position'].value);
    }

    // cut/paste support: this changes the site structure
    var cut_item_pk = null;
    var cut_item = function(pk, elem) {
        var node = get_node(pk);
        if (!node) return;

        var row = $(node.row);
        if (row.hasClass('tree_list_cut')) {
            cut_item_pk = null;
            $('a.tree_list_paste_target', row.parentElement).hide();
            row.removeClass('tree_list_cut');
        } else {
            cut_item_pk = pk;
            $('a.tree_list_paste_target', row.parentElement).show();
            $('tr', row.parentElement).removeClass('tree_list_cut');
            row.addClass('tree_list_cut').find('a.tree_list_paste_target').hide();
        }
        return false;
    }

    var paste_item = function(pk, position) {
        if (!cut_item_pk) return false;
        $.post(
            '.', {
                'tree_list': 'move_node',
                'position': position,
                'cut_item': cut_item_pk,
                'pasted_on': pk,
                'csrfmiddlewaretoken': Cookies.get('csrftoken')
            },
            function(data) {
                var error_message = '', reload = false;
                if (!data) {
                    error_message = 'No data received after request.';
                } else if(data.error == undefined) {
                    // reinitialize tree_structure data
                    tree_list.tree_structure = data;
                    tree_structure_clean();

                    // focus pasted tr if it visible, else focus pasted_on tr
                    tr = $('.tree_list_cut_item[data-item=' + cut_item_pk + ']:visible');
                    tr = tr.length ? tr : $('.tree_list_cut_item[data-item=' + pk + ']');
                    tr.parents('tr').focus();
                } else {
                    error_message = data.error
                }

                if (error_message) {
                    alert('Tree node moving error:\n'
                          + error_message
                          + (reload ? '\n\nThis page will reload now.' : ''));
                    reload && window.location.reload();
                }
            }
        );
        return false;
    }

    // global namespace object
    tree_list = {
        'open_entire_tree': open_entire_tree,
        'close_entire_tree': close_entire_tree,
        'openclose_item': openclose_item,

        'paste_item': paste_item,
        'cut_item': cut_item,

        'tree_structure_clean': tree_structure_clean,
        'tree_structure': {'order': [], 'nodes': {}},
        'tree_state': [],

        'empty_class': 'tree_list_node_leaf',
        'expand_class': 'tree_list_node_closed',
        'collapse_class': 'tree_list_node_opened',

        'changelist_itemid': changelist_itemid,
        'changelist_tab': changelist_tab,
        'changelist_openclose': changelist_openclose,
        'changelist_cutitem': changelist_cutitem,
        'changelist_pasteitem': changelist_pasteitem
    };

    // window onload event
    $(function(){
        // do nothing if not result_list table
        if (!document.getElementById('result_list')) return;

        // reduce structure to actually present items
        tree_structure_clean(initial=true);

        // attach click events
        // open/close subtree events
        for (var i in tree_list.tree_structure.nodes) {
            var node = get_node(i);
            if (!node) continue;
            node.ptr.addEventListener('click', function(event) {
                event.preventDefault();
                openclose_item(this.attributes['data-item'].value);
            });
        }

        // moving node/subtree events (cut)
        var queryset = document.getElementsByClassName('tree_list_cut_item');
        Array.prototype.forEach.call(queryset, function(el, index, collection) {
            el.addEventListener('click', function(event) {
                event.preventDefault();
                cut_item(this.attributes['data-item'].value, this);
            });
        });

        // moving node/subtree events (paste)
        var queryset = document.getElementsByClassName('tree_list_paste_target');
        Array.prototype.forEach.call(queryset, function(el, index, collection) {
            el.addEventListener('click', function(event) {
                event.preventDefault();
                paste_item(this.attributes['data-item'].value,
                           this.attributes['data-position'].value);
            });
        });

        // attach keydown/keypress events on table lines
        $('#result_list tr').keydown(function(event) {
            // 38-up, 40-down, 37-left, 39-right, 10/13-enter
            var status = false;
            switch(event.keyCode) {
                case 38:    event.ctrlKey ? (event.shiftKey
                                             ? changelist_tab($(this), event, -1, true)
                                             : changelist_pasteitem(this, 'left'))
                                          : changelist_tab($(this), event, -1);
                            break; // up
                case 40:    event.ctrlKey ? (event.shiftKey
                                             ? changelist_tab($(this), event, 1, true)
                                             : changelist_pasteitem(this, 'right'))
                                          : changelist_tab($(this), event, 1);
                            break; // down
                case 37:    event.ctrlKey ? (event.shiftKey
                                             ? close_entire_tree() || changelist_tab($(this), event, -1, true)
                                             : changelist_cutitem(this))
                                          : changelist_openclose(this, 0);
                            break; // left
                case 39:    event.ctrlKey ? (event.shiftKey
                                             ? open_entire_tree()
                                             : changelist_pasteitem(this, 'first-child'))
                                          : changelist_openclose(this, 1);
                            break; // right
                case 13:
                case 10:    if (event.ctrlKey) {
                                item_id = changelist_itemid(this);
                                document.location = document.location.pathname + item_id + '/';
                                break;
                            } // return (10 on iphone, 13 anywhere)
                default:    status = true; break; // default behaviour
            }
            return status;
        });

        $('body').keydown(function(event) {
            // 38-up, 40-down
            var status = false;
            switch(event.keyCode) {
                case 38:
                case 40:    if (event.ctrlKey && event.shiftKey) {
                                $('#result_list tbody tr')[event.keyCode == 40 ? 'first' : 'last']().focus();
                            } else {
                                status = true;
                            }
                            break; // up and down
                default:    status = true; break; // default behaviour
            }
            return status;
        });

        // set tabindex to all result_list tr, focus on first one
        $('#result_list tbody tr').attr('tabindex', '0').first().focus();

        // attach click event to expand/collapse button
        document.getElementById('treelist-expand-collapse-tree').addEventListener('click', function(event) {
            event.preventDefault();
            $('#result_list tbody tr:eq(0)').focus();
            if ($('#result_list .tree_list_node_opened:visible').length) {
                tree_list.close_entire_tree();
            } else {
                tree_list.open_entire_tree();
            }
        });
    });

})(django.jQuery);
