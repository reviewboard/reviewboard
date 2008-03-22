RB.dialogs = {}

/*
 * Base dialog class. This is common to all dialogs and sets the default
 * properties, adds buttons, and sets up key bindings.
 */
RB.dialogs.BaseDialog = function(config) {
    this.buttonlist = config.buttons;
    config.buttons = null;

    YAHOO.ext.util.Config.apply(this, config);

    var dh = YAHOO.ext.DomHelper;

    /* The actual dialog element. By default, this is hidden. */
    this.el = dh.append(document.body, {
        tag: 'div',
        style: 'visibility: hidden; position: absolute; top: 0px;',
        cls: config.dialogClass,
        children: [{
            tag: 'div',
            cls: 'ydlg-hd',
            html: this.title
        }]
    }, true);

    /* The main content of the dialog */
    this.bodyEl = dh.append(this.el.dom, {
        tag: 'div',
        cls: 'ydlg-bd'
    }, true);

    RB.dialogs.BaseDialog.superclass.constructor.call(this, this.el, {
        shadow: true,
        width: this.width || 350,
        height: this.height || 200,
        minWidth: this.minWidth || 350,
        minHeight: this.minHeight || 200,
        proxyDrag: true
    });

    this.addKeyListener(27, this.hide, this);

    this.buttons = [];

    if (this.buttonlist) {
        for (var i = this.buttonlist.length - 1; i >= 0; i--) {
            var button = this.addButton(this.buttonlist[i].text,
                this.onButtonPressed.createDelegate(this,
                                                    [this.buttonlist[i].cb]));

            if (this.buttonlist[i].is_default) {
                this.setDefaultButton(button);
            }

            this.buttons.push(button);
        }
    }
}

YAHOO.extendX(RB.dialogs.BaseDialog, YAHOO.ext.BasicDialog, {
    /*
     * Callback handler for when a button is pressed.
     */
    onButtonPressed: function(cb) {
        var should_hide = true;

        if (cb) {
            /*
             * We want to hide unless the callback specifically
             * returns false. If it doesn't return, assume we should
             * hide the dialog.
             */
            should_hide = (cb() != false);
        }

        if (should_hide) {
            this.hide();
        }
    }
});


/*
 * A simple message dialog informing the user of something.
 */
RB.dialogs.MessageDialog = function(config) {
    RB.dialogs.MessageDialog.superclass.constructor.call(this, config);

    dh.append(this.bodyEl.dom, {
        tag: 'h1',
        html: this.summary
    });

    dh.append(this.bodyEl.dom, {
        tag: 'p',
        html: this.description
    });
}

YAHOO.extendX(RB.dialogs.MessageDialog, RB.dialogs.BaseDialog);


/*
 * A dialog displaying a form for input.
 */
RB.dialogs.FormDialog = function(config) {
    /*
     * Form dialogs only need two buttons: A confirmation button, and a
     * cancel button.
     */
    config.buttons = [{
        text: config.confirmButton || "OK",
        cb: this.submit.createDelegate(this)
    }, {
        text: config.cancelButton || "Cancel",
        is_default: true
    }];

    config.dialogClass = "formdlg";

    RB.dialogs.FormDialog.superclass.constructor.call(this, config);

    this.on('hide', function() {
        /*
         * When we hide the dialog, we want to reset the dialog by clearing
         * all fields and all displayed errors.
         */
        this.clearErrors();
        if (this.formEl) {
            this.formEl.dom.reset();
        }
    }, this, true);


    /*
     * The actual <form>
     */
    this.formEl = dh.append(this.bodyEl.dom, {
        tag: 'form',
        action: config.action || ".",
        children: [{
            tag: 'div',
            cls: 'error'
        }]
    }, true);

    this.errorEl = getEl(this.formEl.dom.firstChild);
    this.errorEl.enableDisplayMode();
    this.errorEl.hide();

    /*
     * The table containing the fields and labels.
     */
    this.tableEl = dh.append(this.formEl.dom, {
        tag: 'table',
        children: [{
            tag: 'tbody'
        }]
    }, true);

    var tbody = this.tableEl.dom.firstChild;


    /*
     * A dictionary containing information on each field, for future reference.
     * The dictionary is in the following format:
     *
     * fieldname: {
     *    'field': {
     *        'name':   string,  // Field name,
     *        'hidden': bool,    // Indicates if this is hidden
     *        'label':  string,  // The displayed field label
     *        'widget': string   // HTML describing the field widget
     *    },
     *    'row':      element,   // Table row element for the field
     *    'errorRow': element    // Table row element for the field's error
     * }
     */
    this.fieldInfo = {};

    for (var i = 0; i < config.fields.length; i++) {
        var field = this.fields[i];
        this.fieldInfo[field.name] = {'field': field};

        if (field.hidden) {
            dh.insertHtml("beforeEnd", this.formEl.dom, field.widget);
        } else {
            this.fieldInfo[field.name].row = dh.append(tbody, {
                tag: 'tr',
                children: [{
                    tag: 'td',
                    cls: 'label',
                    html: field.label
                }, {
                    tag: 'td',
                    html: field.widget
                }]
            }, true);

            this.fieldInfo[field.name].errorRow = dh.append(tbody, {
                tag: 'tr'
            }, true);
        }
    }
}

YAHOO.extendX(RB.dialogs.FormDialog, RB.dialogs.BaseDialog, {
    /*
     * Submits the form data to the server. Invoked by pressing the confirm
     * button.
     *
     * @return {bool} false
     */
    submit: function() {
        /* We don't want to stack errors, so get rid of any existing ones. */
        this.clearErrors();

        /* Don't let the user press any buttons while we're doing this. */
        for (b in this.buttons) {
            this.buttons[b].disable();
        }

        var spinnerDiv = null;

        if (this.upload) {
            /*
             * We're uploading, so indicate this with a spinner and
             * "Uploading..." text in the bottom-left of the dialog.
             */
            spinnerDiv = dh.insertBefore(this.buttons[0].el.dom, {
                tag: 'div',
                cls: 'spinner',
                children: [{
                    tag: 'img',
                    src: '../images/dlg-spinner.gif',
                    width: 16,
                    height: 16,
                    alt: ""
                }, {
                    tag: 'h1',
                    html: 'Uploading...'
                }]
            }, true);
        }

        YAHOO.util.Connect.setForm(this.formEl.dom, this.upload);
        asyncJsonRequest("POST", this.path, {
            success: function(rsp) {
                /*
                 * Things went well, so remove the spinner and hide the
                 * dialog.
                 */
                if (spinnerDiv) {
                    spinnerDiv.remove();
                }

                this.hide(this.onSubmitted);
            }.createDelegate(this),

            failure: function(errmsg, rsp) {
                /*
                 * Things went badly, oh noes! Remove the spinner and show
                 * the errors.
                 */
                if (spinnerDiv) {
                    spinnerDiv.remove();
                }

                this.showError(errmsg, rsp);
            }.createDelegate(this)
        }, ""); // The "" prevents the "dummy" value from being sent

        // Prevent the dialog from closing just yet. The callbacks will do it.
        return false;
    },

    /*
     * Shows the errors in the form as returned by the resulting
     * JSON error response.
     *
     * @param {String} text  The main error text.
     * @param {dict}   rsp   The JSON response possibly containing the errors.
     */
    showError: function(text, rsp) {
        if (rsp && rsp.fields) {
            for (var fieldName in rsp.fields) {
                if (!this.fieldInfo[fieldName]) {
                    continue;
                }

                var errorRow = this.fieldInfo[fieldName].errorRow;
                var items = [];

                for (var i = 0; i < rsp.fields[fieldName].length; i++) {
                    items.push({
                        tag: 'li',
                        html: rsp.fields[fieldName][i]
                    })
                }

                dh.append(errorRow.dom, {
                    tag: 'td'
                });

                dh.append(errorRow.dom, {
                    tag: 'td',
                    children: [{
                        tag: 'ul',
                        cls: 'errorlist',
                        children: items
                    }]
                });
            }
        }

        this.errorEl.show();
        this.errorEl.dom.innerHTML = text;

        for (b in this.buttons) {
            this.buttons[b].enable();
        }
    },

    /*
     * Clears all displayed errors from the dialog.
     */
    clearErrors: function() {
        this.errorEl.dom.innerHTML = "";
        this.errorEl.hide();

        for (var fieldName in this.fieldInfo) {
            var errorRow = this.fieldInfo[fieldName].errorRow.dom;
            while (errorRow.cells.length > 0) {
                errorRow.deleteCell(0);
            }
        }
    }
});


/*
 * The registered form dialogs. The structure is as follows:
 *
 * elementId: {
 *     'info': {
 *         'title':         string,   // The title of the dialog
 *         'confirmButton': string,   // The confirm button text (optional)
 *         'cancelButton':  string,   // The cancel button text (optional)
 *         'width':         int,      // Default width of the dialog (optional)
 *         'height':        int,      // Default height of the dialog (optional)
 *         'path':          string,   // The JSON API path to POST to
 *         'upload':        bool,     // Indicates if this is an upload form
 *         'onSubmitted':   function, // Submitted callback function
 *         'fields':        dict      // Dictionary of fields
 *     },
 *     'dialog': element,             // Dialog element
 */
RB.dialogs.gFormDialogs = {};

/*
 * Registers a form dialog for later display.
 *
 * @param {string} elid  The element ID of the link activating this dialog.
 * @param {dict}   info  The dialog information.
 */
RB.dialogs.registerFormDialog = function(elid, info) {
    RB.dialogs.gFormDialogs[elid] = {
        info: info,
        dialog: null
    };
}


/*
 * Shows a registered form dialog.
 *
 * @param {string} elid  The element ID of the link showing the dialog.
 */
RB.dialogs.showFormDialog = function(elid) {
    if (!RB.dialogs.gFormDialogs[elid]) {
        return;
    }

    if (!RB.dialogs.gFormDialogs[elid].dialog) {
        RB.dialogs.gFormDialogs[elid].dialog =
            new RB.dialogs.FormDialog(RB.dialogs.gFormDialogs[elid].info);
    }

    RB.dialogs.gFormDialogs[elid].dialog.show(getEl(elid));
}
