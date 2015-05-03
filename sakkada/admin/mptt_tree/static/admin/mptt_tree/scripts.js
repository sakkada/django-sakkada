(function ($) {
    // recolor table lines if count not too huge
    var recolor_lines = function() {
        $('#result_list tbody tr').removeClass('row1').removeClass('row2');
        $('#result_list tbody tr:visible:even').addClass('row1');
        $('#result_list tbody tr:visible:odd').addClass('row2');
    }

    // get node from tree_structure by id
    var get_node = function(item_id) {
        return mptt_tree.tree_structure.nodes[item_id];
    }

    // show all immediate children, then open all children that are marked as open
    var open_subtree = function(item_id) {
        // vanilla js for speedup
        var node = get_node(item_id);
        if (!node || node.children.length == 0) return;
        node.ptr.classList.remove(mptt_tree.expand_class);
        node.ptr.classList.add(mptt_tree.collapse_class);
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
        node.ptr.classList.remove(mptt_tree.collapse_class);
        node.ptr.classList.add(mptt_tree.expand_class);
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
            mptt_tree.tree_state = mptt_tree.tree_state.filter(function(i) { return i != item_id; });
        } else {
            open_subtree(item_id);
            mptt_tree.tree_state.push(item_id);
        }
        recolor_lines();
    }

    // open all nodes
    var open_entire_tree = function() {
        mptt_tree.tree_state = [];
        var node;
        for (var i in mptt_tree.tree_structure.nodes) {
            node = get_node(i);
            if (node && node.children.length) {
                open_subtree(i);
                mptt_tree.tree_state.push(i);
            }
        }
        recolor_lines();
    }

    // close all nodes
    var close_entire_tree = function() {
        for (var i in mptt_tree.tree_structure.nodes) {
            node = get_node(i);
            if (node && node.children.length) {
                close_subtree(i);
            }
        }
        mptt_tree.tree_state = [];
        recolor_lines();
    }

    // prepare tree_structure on-init/after-response
    var tree_structure_clean = function(initial) {
        initial = initial === true ? true : false;

        // prepare structure: set row and pointer (marker) variables
        //                    if it exists else set node value to null
        for(var i in mptt_tree.tree_structure.nodes) {
            var node = mptt_tree.tree_structure.nodes[i];
            var marker = document.getElementById('mtree_node_marker-' + i);
            if(marker) {
                node.ptr = marker;
                node.row = marker.parentElement.parentElement;
            } else {
                mptt_tree.tree_structure.nodes[i] = null;
            }
        }

        if (!initial) {
            // restore initial state
            for (var i in mptt_tree.tree_structure.nodes) {
                var node = get_node(i);
                if (!node) continue;

                // restore marker class
                node.ptr.classList.remove(mptt_tree.expand_class);
                node.ptr.classList.remove(mptt_tree.collapse_class);
                node.ptr.classList.add(mptt_tree.empty_class);

                // indent nodes
                var indent = $(node.ptr).prev()[0];
                indent.innerHTML = Array(node.level+1).join('.&nbsp;&nbsp;&nbsp;');
            }

            // order rows by tree_structure.order
            var last = 0, node = null,
                result_list = document.querySelector('#result_list tbody');
            for (var i in mptt_tree.tree_structure.order) {
                node = get_node(mptt_tree.tree_structure.order[i]);
                if (!node) continue;
                result_list.insertBefore(node.row, result_list.getElementsByTagName('tr')[last]);
                last++;
            }
        } else {
            // get opened nodes list from cookies (once per request)
            mptt_tree.tree_state = Cookies.get('django_admin_mptt_tree_state');
            if (mptt_tree.tree_state) {
                mptt_tree.tree_state = mptt_tree.tree_state.split('-');
                mptt_tree.tree_state.forEach(function(el, i){ this[i] = parseInt(el) },
                                             mptt_tree.tree_state);
            } else {
                mptt_tree.tree_state = [];
            }

            $(window).unload(function() {
                // save a list of open nodes state across reloads
                Cookies.set('django_admin_mptt_tree_state', mptt_tree.tree_state.join('-'), {'path':'/'});
            })
        }

        // clean out tree_structure: remove non existant parents, children,
        //                           descendants; update markers
        for (var i in mptt_tree.tree_structure.nodes) {
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
                    node.ptr.classList.remove(mptt_tree.empty_class);
                    node.ptr.classList.add(mptt_tree.expand_class);
                }
            }
        }

        // mark nodes from tree_state as open if it not deleted
        for (var i in mptt_tree.tree_state) {
            var node = get_node(mptt_tree.tree_state[i]);
            if (node) {
                node.open = true;
            }
        }

        // get root_items and hide all rows
        var root_items = [];
        for (var i in mptt_tree.tree_structure.nodes) {
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
        return $('span.mtree_node_marker', elem).attr('data-item');
    }

    var changelist_tab = function(elem, event, direction) {
        event.preventDefault();
        ((direction > 0) ? elem.nextAll() : elem.prevAll()).filter(':visible:eq(0)').focus();
    }

    var changelist_openclose = function(elem, openclose) {
        var item_id = changelist_itemid(elem),
            node = get_node(item_id);
        if (node && ((openclose && !node.open) || (!openclose && node.open))) {
            openclose_item(item_id);
        }
    }

    var changelist_cutitem = function(tr) {
        var icut = tr.getElementsByClassName('mtree_cut_item')[0];
        cut_item(icut.attributes['data-item'].value, icut);
    }

    var changelist_pasteitem = function(tr, position) {
        var target = $(tr).find('.mtree_paste_target[data-position='+position+']:visible');
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
        if (row.hasClass('mtree_cut')) {
            cut_item_pk = null;
            $('a.mtree_paste_target', row.parentElement).hide();
            row.removeClass('mtree_cut');
        } else {
            cut_item_pk = pk;
            $('a.mtree_paste_target', row.parentElement).show();
            $('tr', row.parentElement).removeClass('mtree_cut');
            row.addClass('mtree_cut').find('a.mtree_paste_target').hide();
        }
        return false;
    }

    var paste_item = function(pk, position) {
        if (!cut_item_pk) return false;
        $.post(
            '.', {
                '__cmd__': 'move_node',
                'position': position,
                'cut_item': cut_item_pk,
                'pasted_on': pk,
                'csrfmiddlewaretoken': Cookies.get('csrftoken')
            },
            function(data) {
                var error_message = '';
                if(data.slice(0,2) == 'OK') {
                    data = data[2] == '{' && data.slice(-1) == '}' ? data.slice(2) : '{}';
                    try { data = $.parseJSON(data); }
                    catch (err) { error_message = 'Error: JSON parsing error.'; }
                    if (!data) {
                        error_message = 'Error: No data received after request.';
                    }
                    if (error_message) {
                        alert(error_message); return;
                    }

                    // reinitialize tree_structure data
                    mptt_tree.tree_structure = data;
                    mptt_tree.tree_structure && tree_structure_clean();

                    // focus pasted tr if it visible, else focus pasted_on tr
                    tr = $('.mtree_cut_item[data-item='+cut_item_pk+']:visible');
                    tr = tr.length ? tr : $('.mtree_cut_item[data-item='+pk+']');
                    tr.parents('tr').focus();
                } else {
                    alert(data + '\nThis page will reload now.');
                    window.location.reload();
                }
            }
        );
        return false;
    }

    // global namespace object
    mptt_tree = {
        'open_entire_tree': open_entire_tree,
        'close_entire_tree': close_entire_tree,
        'openclose_item': openclose_item,

        'paste_item': paste_item,
        'cut_item': cut_item,

        'tree_structure_clean': tree_structure_clean,
        'tree_structure': {'order': [], 'nodes': {}},
        'tree_state': [],

        'empty_class': 'mtree_node_leaf',
        'expand_class': 'mtree_node_closed',
        'collapse_class': 'mtree_node_opened',

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
        for (var i in mptt_tree.tree_structure.nodes) {
            var node = get_node(i);
            if (!node) continue;
            node.ptr.addEventListener('click', function(event) {
                event.preventDefault();
                openclose_item(this.attributes['data-item'].value);
            });
        }

        // moving node/subtree events (cut)
        var queryset = document.getElementsByClassName('mtree_cut_item');
        Array.prototype.forEach.call(queryset, function(el, index, collection) {
            el.addEventListener('click', function(event) {
                event.preventDefault();
                cut_item(this.attributes['data-item'].value, this);
            });
        });

        // moving node/subtree events (paste)
        var queryset = document.getElementsByClassName('mtree_paste_target');
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
                case 38:    event.ctrlKey ? changelist_pasteitem(this, 'left')
                                          : changelist_tab($(this), event, -1);
                            break; // up
                case 40:    event.ctrlKey ? changelist_pasteitem(this, 'right')
                                          : changelist_tab($(this), event, 1);
                            break; // down
                case 37:    event.ctrlKey ? changelist_cutitem(this)
                                          : changelist_openclose(this, 0);
                            break; // left
                case 39:    event.ctrlKey ? changelist_pasteitem(this, 'first-child')
                                          : changelist_openclose(this, 1);
                            break; // right
                case 13:
                case 10:    if (event.ctrlKey) {
                                item_id = changelist_itemid(this);
                                document.location = document.location.pathname + item_id + '/';
                                break;
                            } // return (10 on iphone, 13 anywhere)
                default:    status = true; break;
            }
            return status;
        }).keypress(function(event) {
            var status = false;
            switch(event.charCode) {
                case 43:    open_entire_tree(); break;  // +
                case 45:    close_entire_tree(); break; // -
                default:    status = true; break;
            }
            return status;
        });

        // set tabindex to all result_list tr, focus on first one
        $('#result_list tr').attr('tabindex', '0');
        $('#result_list tr:eq(1)').focus();

        // show shortcuts to expand/collapse tree
        var mtree_filter = $('#mtree-changelist-filter');
        if (mtree_filter.length) {
            // move changelist-filter-shortcuts into changelist-filter
            var shortcuts_list = $('#changelist-filter .changelist-filter-shortcuts');
            if (shortcuts_list.length) {
                shortcuts_list.append(mtree_filter.find('ul li'));
            } else {
                $('#changelist-filter').prepend(mtree_filter.children());
            }
            mtree_filter.remove();

            // attach click event
            document.getElementById('mtree-expand-collapse-tree').addEventListener('click', function(event) {
                event.preventDefault();
                if ($('#result_list .mtree_node_opened:visible').length) {
                    mptt_tree.close_entire_tree();
                } else {
                    mptt_tree.open_entire_tree();
                }
            });
        }
    });

})(django.jQuery);
