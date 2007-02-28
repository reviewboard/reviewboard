RB.widgets = {}

/**
 * Class that provides an inline editor field for single-line or multi-line
 * blocks of text.
 */
RB.widgets.InlineEditor = function(config) {
	YAHOO.ext.util.Config.apply(this, config);

	var dh = YAHOO.ext.DomHelper;

	this.el = getEl(this.el);
	this.el.enableDisplayMode();

	this.form = dh.insertBefore(this.el.dom, {
		tag: 'form',
		cls: 'inline-editor-form ' + (this.cls || ''),
	}, true);
	this.form.enableDisplayMode();

	var saveButton = {
		tag: 'input',
		type: 'submit',
		value: 'Save',
		cls: 'save',
	};

	var cancelButton = {
		tag: 'input',
		type: 'submit',
		value: 'Cancel',
		cls: 'cancel',
	};

	if (this.multiline) {
		this.field = this.form.createChild({
			tag: 'textarea',
			html: this.value || '',
			wrap: 'none',
			rows: 10,
			cols: 80,
		});

		block = this.form.createChild({tag: 'div'});
		this.saveButton = block.createChild(saveButton);
		this.cancelButton = block.createChild(cancelButton);
	} else {
		this.field = this.form.createChild({
			tag: 'input',
			type: 'text',
		});

		this.saveButton = this.form.createChild(saveButton);
		this.cancelButton = this.form.createChild(cancelButton);
	}

	this.saveButton.enableDisplayMode();
	this.cancelButton.enableDisplayMode();

	if (this.showEditIcon) {
		var img = {
			tag: 'img',
			cls: 'editicon',
			src: '/images/edit.png',
			width: 20,
			height: 14,
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
	};

	if (!this.useEditIconOnly) {
		this.el.on('click', this.startEdit, this, true);
	}

	this.saveButton.on('click', this.save, this, true);
	this.cancelButton.on('click', this.cancel, this, true);

	this.field.addKeyMap([
		{
			key: [10, 13],
			fn: this.onEnter,
			scope: this,
		},
		{
			key: 27,
			fn: this.onEscape,
			scope: this,
		}
	]);

	YAHOO.ext.EventManager.onWindowResize(this.fitWidthToParent, this, true);

	this.hide();
}

YAHOO.extendX(RB.widgets.InlineEditor, YAHOO.ext.util.Observable, {
	onEnter: function(k, e) {
		if (!this.multiline || e.ctrlKey) {
			this.save();
		}
	},

	onEscape: function() {
		this.cancel();
	},

	startEdit: function() {
		this.initialValue = this.el.dom.innerHTML;
		var value = this.normalizeText(this.htmldecode(this.el.dom.innerHTML));
		this.setValue(value);
		this.editing = true;
		this.show();
		this.fireEvent('beginedit', this);
	},

	completeEdit: function() {
		var value = this.htmlencode(this.getValue());
		this.el.dom.innerHTML = value;

		this.hide();
		this.editing = false;

		if (this.normalizeText(this.htmldecode(this.initialValue)) != value ||
		    this.notifyUnchangedCompletion) {
			this.fireEvent('complete', this, value, this.initialValue);
		}
	},

	htmldecode: function(str) {
		if (str == "") {
			return str;
		}

		str = str.replace(/&amp;/g, "&");
		str = str.replace(/&lt;/g, "<");
		str = str.replace(/&gt;/g, ">");
		return str;
	},

	htmlencode: function(str) {
		if (str == "") {
			return str;
		}

		str = str.replace(/&/g, "&amp;");
		str = str.replace(/</g, "&lt;");
		str = str.replace(/>/g, "&gt;");
		return str;
	},

	normalizeText: function(str) {
		if (this.stripTags) {
		  str = str.stripTags().strip();
		}

		if (!this.multiline) {
			return str.replace(/\s{2,}/g, " ");
		}

		return str;
	},

	save: function(e) {
		if (e) {
			e.preventDefault();
		}

		this.completeEdit();
	},

	cancel: function(e) {
		if (e) {
			e.preventDefault();
		}
		this.el.dom.innerHTML = this.initialValue;
		this.hide();
		this.editing = false;
	},

	show: function() {
		if (this.editicon) {
			this.editicon.hide(this.multiline);
		}

		if (!this.hideButtons) {
			this.saveButton.show();
			this.cancelButton.show();
		}

		this.el.hide();
		this.form.show();

		if (this.multiline) {
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
		this.saveButton.hide();
		this.cancelButton.hide();
		this.field.blur();

		if (this.editicon) {
			this.editicon.show(this.multiline);
		}

		if (this.multiline && this.editing) {
			this.field.setStyle("overflow", "hidden");
			this.el.beginMeasure();
			var elHeight = this.el.getBox(true, true).height;
			this.el.endMeasure();

			this.field.setHeight(
				elHeight + this.field.getBorderWidth('tb') +
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
		if (this.editing) {
			if (this.multiline) {
				this.form.setWidth(getEl(this.form.dom.parentNode).getWidth());
				this.field.setWidth(this.form.getWidth());
			} else {
				var parentWidth = getEl(this.el.dom.parentNode).getWidth();
				var elWidth = this.el.getWidth();

				this.form.setWidth(
					Math.min(elWidth + (parentWidth - elWidth) / 2,
							 parentWidth));

				var saveButtonX = this.saveButton.getX();
				var buttonsWidth =
					this.cancelButton.getX() - saveButtonX +
					this.cancelButton.getWidth() +
					saveButtonX - (this.field.getX() + this.field.getWidth());
				this.field.setWidth(this.form.getWidth() - buttonsWidth);
			}
		}
	},

	findLabelForId: function(id) {
		var method = function(el) {
			return (el.getAttribute('for') == id);
		};

		return YAHOO.util.Dom.getElementsBy(method, 'label', document);
	},
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
	},
});


RB.widgets.AutosizeTextArea = function(el, config) {
	YAHOO.ext.util.Config.apply(this, config);

	this.el = getEl(el);
	this.el.setStyle("overflow", "hidden");

	this.size = parseFloat(this.el.getStyle('height') || '100');
	this.resizeStep = this.resizeStep || 10;
	this.minHeight = this.minHeight || this.size;

	this.events = {
		'resize': true,
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
	},
});
