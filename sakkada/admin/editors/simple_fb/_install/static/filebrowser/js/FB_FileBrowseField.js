function FileSubmit(FilePath, FileURL, ThumbURL, FileType) {

    // fix: get querystring (GET) params
    var getUrlVars = function() {
        var vars = [], hash;
        var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
        for(var i = 0; i < hashes.length; i++) {
            hash = hashes[i].split('=');
            vars.push(hash[0]);
            vars[hash[0]] = hash[1];
        }
        return vars;
    }

    // var input_id=window.name.split("___").join(".");
    var input_id=window.name.replace(/____/g,'-').split("___").join(".");
    var preview_id = 'preview_' + input_id;
    var previewlink_id = 'previewlink_' + input_id;
    var previewimage_id = 'previewimage_' + input_id;
    input = opener.document.getElementById(input_id);
    preview = opener.document.getElementById(preview_id);
    previewlink = opener.document.getElementById(previewlink_id);
    previewimage = opener.document.getElementById(previewimage_id);
    // set new value for input field (fix: allow to return FileURL instead
    //                                     of FilePath if geturl param exists)
    // input.value = FilePath;
    input.value = getUrlVars()['geturl'] ? FileURL: FilePath;

    if (ThumbURL && FileType != "") {
        // selected file is an image and thumbnail is available:
        // display the preview-image (thumbnail)
        // link the preview-image to the original image
        previewlink.setAttribute("href", FileURL);
        previewlink.setAttribute("target", "_blank");
        previewimage.setAttribute("src", ThumbURL);
        preview.setAttribute("style", "display:block");
    } else {
        // hide preview elements
        previewlink.setAttribute("href", "");
        previewlink.setAttribute("target", "");
        previewimage.setAttribute("src", "");
        preview.setAttribute("style", "display:none");
    }
    this.close();

}
