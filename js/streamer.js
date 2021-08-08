var last_page = '';
var new_page = '';
var $last_elems;

function update() {
    console.debug('Setting masonry grid');
    $('.row').masonry({percentPosition: true});
}

// add next page to grid
function append() {
    console.debug('Last: ', last_page);
    next_page_link = $(".next-page").attr('href');
    if (last_page == next_page_link) {
        console.debug('Already added');
    } else {
        last_page = next_page_link;
        console.debug('Adding: ', next_page_link);
        //$(".row").append("Some appended text.");
        $.get(next_page_link + '?infinite=true', function (data, status) {
            // make jQuery object
            $last_elems = $(data);
            // add jQuery object
            $('.row').append($last_elems).masonry('appended', $last_elems);
            // wait images to be loaded
            setTimeout(update, 2000);
            // Update next page url replace last 5 letters with new id
            // maybe use split('/')
            new_page = last_page.slice(0, -6) + $last_elems.get(-1).id; 
            $(".next-page").attr('href', new_page)
            // enable scroll events
            $(window).on("scroll", scroll_event);
        });
    };
}

// wait for scroll
function scroll_event() {
    let scroll_top = $(window).scrollTop();
    console.debug('scroll_top: ', scroll_top);
    let scroll_height = document.body.parentElement.scrollHeight;
    let client_height = document.body.parentElement.clientHeight;
    let pixels_togo = scroll_height - (scroll_top + client_height);
    if (pixels_togo < 2000) {
        // disable scroll events
        $(window).off("scroll", scroll_event);
        append();
    };
}

// wait for images to be loaded
$(window).on("load", function () {
    update();
    setTimeout(update, 2000);

    // add images if there is no scroll bar
    let scroll_height = document.body.parentElement.scrollHeight;
    let client_height = document.body.parentElement.clientHeight;
    while (scroll_height == client_height) {
        scroll_height = document.body.parentElement.scrollHeight;
        client_height = document.body.parentElement.clientHeight;
        append();
        break;
    };
    // enable scroll events
    $(window).on("scroll", scroll_event);
});
