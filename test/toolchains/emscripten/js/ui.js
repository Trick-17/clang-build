$(document).ready(function()
{
    $('form').attr('onsubmit', 'return false;');

    Module_Backend().then(function(Module) {
        Module._print_hi();
        var x = Module._return_x();
        document.getElementById('label-libversion').textContent="Backend returned x = " + x;
    });
});