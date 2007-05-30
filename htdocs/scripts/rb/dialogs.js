RB.dialogs = {}

RB.dialogs.MessageDialog = function(config) {
  this.buttonlist = config.buttons;
  config.buttons = null;

	YAHOO.ext.util.Config.apply(this, config);

  var dh = YAHOO.ext.DomHelper;

  this.el = dh.append(document.body, {
    tag: 'div',
    style: 'visibility: hidden; position: absolute; top: 0px;',
    children: [{
      tag: 'div',
      cls: 'ydlg-hd',
      html: this.title
    }, {
      tag: 'div',
      cls: 'ydlg-bd',
      children: [{
        tag: 'h1',
        html: this.summary
      }, {
        tag: 'p',
        html: this.description
      }]
    }]
  }, true);

  RB.dialogs.MessageDialog.superclass.constructor.call(this, this.el, {
    shadow: true,
    width: this.width || 350,
    height: this.height || 200,
    minWidth: this.minWidth || 350,
    minHeight: this.minHeight || 200,
    proxyDrag: true
  });

  this.addKeyListener(27, this.hide, this);

  if (this.buttonlist) {
    for (var i = 0; i < this.buttonlist.length; i++) {
      var button = this.addButton(this.buttonlist[i].text, function(cb) {
        this.hide();

        if (cb) {
          cb();
        }
      }.createDelegate(this, [this.buttonlist[i].cb]));

      if (this.buttonlist[i].is_default) {
        this.setDefaultButton(button);
      }
    }
  }
}

YAHOO.extendX(RB.dialogs.MessageDialog, YAHOO.ext.BasicDialog);
