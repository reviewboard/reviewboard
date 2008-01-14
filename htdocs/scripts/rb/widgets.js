RB.widgets = {}

/**
 * Class that provides an inline editor field for single-line or multi-line
 * blocks of text.
 */
RB.widgets.InlineEditor = function(config) {
    YAHOO.ext.util.Config.apply(this, config);

    /* Define our keymap so we can register it later. */
    keymap = [{
            key: [10, 13],
            fn: this.onEnter,
            scope: this
        },
        {
            key: 27,
            fn: this.onEscape,
            scope: this
        }
    ];

    var dh = YAHOO.ext.DomHelper;

    this.el = getEl(this.el);
    this.el.enableDisplayMode();

    this.form = dh.insertBefore(this.el.dom, {
        tag: 'form',
        cls: 'inline-editor-form ' + (this.cls || '')
    }, true);
    this.form.enableDisplayMode();

    /*
     * Rather than animating on IE, the icon just simply disappears and
     * never comes back. So disable animations.
     */
    this.animateIcon =
        this.multiline && (navigator.appVersion.indexOf("MSIE") == -1);

    if (this.multiline) {
        this.field = this.form.createChild({
            tag: 'textarea',
            html: this.value || ''
        });

        var autoSizeArea = new RB.widgets.AutosizeTextArea(this.field, {
            autoGrowVertical: true
        });

        block = this.form.createChild({tag: 'div'});
        this.saveButton = block.createChild({
            tag: 'input',
            type: 'submit',
            value: 'OK',
            cls: 'save'
        });

        this.cancelButton = block.createChild({
            tag: 'input',
            type: 'submit',
            value: 'Cancel',
            cls: 'cancel'
        });

        this.saveButton.enableDisplayMode();
        this.cancelButton.enableDisplayMode();
        this.saveButton.hide();
        this.cancelButton.hide();

        this.saveButton.on('click', this.save, this, true);
        this.cancelButton.on('click', this.cancel, this, true);

    } else if (this.autocomplete) {
        var auto_id = 'autoComplete_' + this.cls;
        var autoinput_id = 'autoInput_' + this.cls;
        var container_id = "ysearchcontainer_" + this.cls;

        this.skin = this.form.createChild({
            tag: 'div',
            cls: 'yui-skin-sam'
        });

        this.autodiv = this.skin.createChild({
            tag: 'div',
            id:  auto_id,
            cls: 'yui-ac'
        });

        this.field = this.autodiv.createChild({
            tag:  'input',
            type: 'text',
            id:   autoinput_id,
            cls:  'yui-ac-input'
        });

        this.autodiv.createChild({
            tag: 'div',
            id:  container_id,
            cls: 'yui-ac-container'
        });

        this.left = this.skin.createChild({
            tag:   'div',
            style: 'float: right;'
        });

        /*
         * Do this before creating the AutoComplete so we can listen to
         * the key presses first.
         */
        this.field.addKeyMap(keymap);

        var autoComp = new YAHOO.widget.AutoComplete(autoinput_id,
                                                     container_id,
                                                     this.autocomplete, {
            animVert: false,
            animHoriz: false,
            typeAhead: false,
            allowBrowserAutocomplete: false,
            prehighlightClassName: "yui-ac-prehighlight",
            delimChar: [",", " "],
            minQueryLength: 1,
            queryDelay: 0,
            useShadow: true
        });
        autoComp.setFooter("Press Tab to auto-complete.");
    } else {
        this.field = this.form.createChild({
            tag: 'input',
            type: 'text'
        });

        this.field.addKeyMap(keymap);
    }

    if (this.showEditIcon) {
        var img = {
            tag: 'img',
            cls: 'editicon',
            src: '/images/edit.png',
            width: 20,
            height: 14
        };

        if (this.multiline) {
            var labels = this.findLabelForId(this.el.id);

            if (labels.length > 0) {
                this.editicon = dh.append(labels[0], img, true);
            }
        } else {
            this.editicon = dh.insertAfter(this.el.dom, img, true);
        }

        if (this.editicon) {
            this.editicon.enableDisplayMode();
            this.editicon.on('click', this.startEdit, this, true);
        }
    }

    this.events = {
        'complete': true,
        'beginedit': true,
        'cancel': true
    };

    if (!this.useEditIconOnly) {
        this.el.on('click', this.startEdit, this, true);
    }

    YAHOO.ext.EventManager.onWindowResize(this.fitWidthToParent, this, true);

    this.hide();
}

YAHOO.extendX(RB.widgets.InlineEditor, YAHOO.ext.util.Observable, {
    onEnter: function(k, e) {
        if (!this.multiline || e.ctrlKey) {
            this.save(e);
        }
    },

    onEscape: function() {
        this.cancel();
    },

    startEdit: function() {
        if (this.el.dom.firstChild && this.el.dom.firstChild.tagName == "PRE") {
            this.initialValue = this.el.dom.firstChild.innerHTML;
        } else {
            this.initialValue = this.el.dom.innerHTML;
        }
        this.setValue(this.normalizeText(this.initialValue).htmlDecode());
        this.editing = true;
        this.show();
        this.fireEvent('beginedit', this);
    },

    completeEdit: function() {
        var value = this.getValue();
        var encodedValue = value.htmlEncode();
        this.el.dom.innerHTML = encodedValue;

        this.hide();
        this.editing = false;

        if (this.normalizeText(this.initialValue) != encodedValue ||
            this.notifyUnchangedCompletion) {
            this.fireEvent('complete', this, value, this.initialValue);
        }
    },

    normalizeText: function(str) {
        if (this.stripTags) {
            /*
             * Turn <br>s back into newlines before stripping out all other
             * tags.  Without this, we lose multi-line data when editing an old
             * comment.
             */
            str = str.replace(/\<br\>/g, '\n');
            str = str.stripTags().strip();
        }

        if (!this.multiline) {
            return str.replace(/\s{2,}/g, " ");
        }

        return str;
    },

    save: function(e) {
        if (e) {
            YAHOO.util.Event.preventDefault(e);
        }

        this.completeEdit();
    },

    cancel: function(e) {
        if (e) {
            YAHOO.util.Event.preventDefault(e);
        }
        this.el.dom.innerHTML = this.initialValue;
        this.hide();
        this.editing = false;
        this.fireEvent('cancel', this, this.initialValue);
    },

    show: function() {
        if (this.editicon) {
            this.editicon.hide(this.animateIcon);
        }

        this.el.hide();
        this.form.show();

        if (this.multiline) {
            if (!this.hideButtons) {
                this.saveButton.show();
                this.cancelButton.show();
            }

            this.el.beginMeasure();
            var elHeight = this.el.getHeight();
            this.el.endMeasure();

            this.field.setStyle("overflow", "hidden");
            this.fitWidthToParent();
            this.field.setHeight(elHeight);
            this.field.setHeight(elHeight + 100, true, 0.35,
            this.finishShow.createDelegate(this));
        } else {
            this.finishShow();
        }
    },

    hide: function() {
        this.field.blur();

        if (this.editicon) {
            this.editicon.show(this.animateIcon);
        }

        if (this.multiline && this.editing) {
            this.saveButton.hide();
            this.cancelButton.hide();

            this.field.setStyle("overflow", "hidden");
            this.el.beginMeasure();
            var elHeight = this.el.getBox(true, true).height;
            this.el.endMeasure();

            this.field.setHeight(elHeight + this.field.getBorderWidth('tb') +
                                 this.field.getPadding('tb'), true, 0.35,
                                 this.finishHide.createDelegate(this));
        } else {
            this.finishHide();
        }
    },

    finishShow: function() {
        if (this.multiline) {
            this.field.setStyle("overflow", "auto");
        }

        this.fitWidthToParent();
        this.field.focus();

        if (!this.multiline) {
            this.field.dom.select();
        }
    },

    finishHide: function() {
        this.el.show();
        this.form.hide();
    },

    setValue: function(value) {
        this.field.dom.value = value;
    },

    getValue: function() {
        return this.field.dom.value;
    },

    fitWidthToParent: function() {
        if (!this.editing) {
            return;
        }

        if (this.multiline) {
            var formParent = getEl(this.form.dom.parentNode);
            formParent.beginMeasure();
            var parentWidth = formParent.getBox(true, true).width;
            formParent.endMeasure();

            this.field.setWidth(parentWidth);
        } else {
            this.el.beginMeasure();
            var elWidth = this.el.getBox(true, true).width +
                          this.el.getPadding("lr") +
                          this.el.getBorderWidth("lr");
            this.el.endMeasure();

            this.field.setWidth(elWidth);
        }
    },

    findLabelForId: function(id) {
        var method = function(el) {
            // FireFox wants "for", IE wants "htmlFor"
            return (el.getAttribute("for") == id ||
                    el.getAttribute("htmlFor") == id);
        };

        return YAHOO.util.Dom.getElementsBy(method, 'label', document);
    }
});


/**
 * Subclass of InlineEditor that is designed for handling comma-separated
 * lists.
 */
RB.widgets.InlineCommaListEditor = function(config) {
    RB.widgets.InlineCommaListEditor.superclass.constructor.call(this, config);

    this.stripTags = true;
};

YAHOO.extendX(RB.widgets.InlineCommaListEditor, RB.widgets.InlineEditor, {
    getList: function() {
        return this.getValue().split(/,\s*/);
    }
});


RB.widgets.AutosizeTextArea = function(el, config) {
    YAHOO.ext.util.Config.apply(this, config);

    this.el = getEl(el);
    this.el.setStyle("overflow", "hidden");

    this.size = parseFloat(this.el.getStyle('height') || '100');
    this.resizeStep = this.resizeStep || 10;
    this.minHeight = this.minHeight || this.size;

    this.events = {
        'resize': true
    };

    if (this.autoGrowVertical) {
        this.el.on('keyup', this.autoGrow, this, true);
        this.autoGrow();
    }
}

YAHOO.extendX(RB.widgets.AutosizeTextArea, YAHOO.ext.util.Observable, {
    autoGrow: function() {
        this.shrink();
        this.grow();
        this.fireEvent('resize', this);
    },

    shrink: function() {
        if (this.size <= this.minHeight + this.resizeStep) {
            return;
        }

        if (this.el.dom.scrollHeight <= this.el.dom.clientHeight) {
            this.size -= 2;
            this.el.setHeight(this.getHeight());
            this.shrink();
        }
    },

    grow: function() {
        if (this.el.dom.scrollHeight > this.el.dom.clientHeight) {
            this.size += 2;
            this.el.setHeight(this.getHeight());
            this.grow();
        }
    },

    getHeight: function() {
        return this.size + this.resizeStep;
    }
});

// vim: set et:
