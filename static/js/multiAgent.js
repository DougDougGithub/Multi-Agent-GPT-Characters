import Letterize from "https://cdn.skypack.dev/letterizejs@2.0.0";
import anime from "https://cdn.skypack.dev/animejs@3.2.1";

$(document).ready(function() {

    var socket = io();

    socket.on('start_agent', function(msg, cb) {
        console.log("Got data: " + msg)

        $('#agent-container-' + msg.agent_id).animate({ opacity: 1 }, 500);

        if (cb)
            cb();
    });

    // Updates each sentence
    socket.on('agent_message', function(msg, cb) {
        
        $("#agent-text-" + msg.agent_id).text(msg.text)
        
        // Note that openAiAnimation is NOT a const variable
        let openAiAnimation = new Letterize({targets: "#agent-text-" + msg.agent_id, className: "agent-letter"});

        // Now we've turned every letter into its own span, we group all of the letter spans into "word" elements, so that the word elements can wrap around multiple lines appropriately
        let $openaiText = $('#agent-text-' + msg.agent_id); // Get the openai-text container
        let $letters = $openaiText.find('.agent-letter'); // Get all the letter spans inside the openai_text container
        let $newContent = $('<div></div>'); // Create a new jQuery object to hold the new structure
        let $wordSpan = $('<span class="agent-word"></span>'); // Create a new word span to start with
        // Iterate over each letter span to create the word element
        $letters.each(function() {
            const $letter = $(this);
            if ($letter.text().trim() === '') { // Check if the letter is a space
                $newContent.append($wordSpan); // Append the current word span to the new content
                $newContent.append($letter); // Add the space directly to the new content
                $wordSpan = $('<span class="agent-word"></span>'); // Create a new word span for the next word
            } else {
                $wordSpan.append($letter); // If not a space, append the letter to the current word span
            }
        });
        $newContent.append($wordSpan); // Append the last word span to the new content
        $openaiText.empty().append($newContent.contents()); // Clear the openai_text container and append the new content

        var animation = anime.timeline({
            targets: openAiAnimation.listAll,
            delay: anime.stagger(30),
            loop: true
        });
        animation
            .add({translateY: -2, duration: 1000})
            .add({translateY: 0, duration: 1000});

        if (cb)
            cb();
    });

    socket.on('clear_agent', function (msg, cb) {
        console.log("Client received clear message instruction!")

        $('#agent-container-' + msg.agent_id).animate({ opacity: 0 }, 500);

        if (cb)
            cb();
    });
});