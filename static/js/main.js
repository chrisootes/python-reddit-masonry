var last_page = '';
var new_page = '';
var $last_elems;

function update() {
    console.debug('Setting masonry grid');
    $('.row').masonry({percentPosition: true});
}

// Add next page to grid
function append() {
    console.debug('Last: ', last_page);
    // The link to next pages is in a href with class next-page
    next_page_link = $(".next-page").attr('href');
    // Check if next page is already is added to prevent duplicates
    if (last_page == next_page_link) {
        console.debug('Already added');
    } else {
        last_page = next_page_link;
        next_page_raw = next_page_link + '&raw=true'
        console.debug('Adding: ', next_page_raw);
        // Request next page
        // With ?items_only=true we dont have to find de items on the page DOM
        // It gives only the html code with items
        $.get(next_page_raw, function (data, status) {
            // Make jQuery object
            $last_elems = $(data);
            // Add jQuery object and update masonry
            $('.row').append($last_elems).masonry('appended', $last_elems);
            // Wait images to be loaded and update masonry again
            setTimeout(update, 2000);
            // Replace next page url with new one
            // The last 5 characters of the path are the id of last post
            // TODO use libary to parse and create url
            new_page_link = last_page.split('?')[0] + '?after=' + $last_elems.get(-1).id; 
            $(".next-page").attr('href', new_page_link)
            // Enable scroll events
            $(window).on("scroll", scroll_event);
        });
    };
}

// Handle scroll event
function scroll_event() {
    let scroll_top = $(window).scrollTop();
    console.debug('Scroll position: ', scroll_top);
    let scroll_height = document.body.parentElement.scrollHeight;
    let client_height = document.body.parentElement.clientHeight;
    let pixels_togo = scroll_height - (scroll_top + client_height);
    if (pixels_togo < 2000) {
        // Disable scroll events so we don't get million updates
        $(window).off("scroll", scroll_event);
        // Append new posts
        append();
    };
}

// Wait for images to be loaded
$(window).on("load", function () {
    // Update masonry
    update();
    setTimeout(update, 2000);

    // Add images if there is no scroll bar
    // If there is no scroll bar than there are no scroll events 
    let scroll_height = document.body.parentElement.scrollHeight;
    let client_height = document.body.parentElement.clientHeight;
    while (scroll_height == client_height) {
        scroll_height = document.body.parentElement.scrollHeight;
        client_height = document.body.parentElement.clientHeight;
        // Append new posts
        append();
        // TODO remove
        break;
    };
    // Enable scroll events
    $(window).on("scroll", scroll_event);
});
