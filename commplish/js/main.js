


function login
$('<iframe />', {"name":"autologin","id":"autologin", "style":"display:none;",
    "src":"/openid?openid_url="+$.cookie('idprovider')}).appendTo('body');
}
