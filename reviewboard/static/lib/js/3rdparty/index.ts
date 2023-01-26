/* Load the jQuery-related modules */
import 'jquery-flot';
import 'jquery-flot/jquery.flot.pie';
import 'jquery-flot/jquery.flot.selection';
import 'jquery-flot/jquery.flot.time';
import { default as setupJQueryForm } from 'jquery-form';
import 'jquery.cookie';
import './jquery.timesince';
import './ui.autocomplete';

/* Load moment and utilities. */
import moment from 'moment';
import 'moment-timezone/builds/moment-timezone-with-data-10-year-range';

/* Load CodeMirror and addons. */
import CodeMirror from 'codemirror';
import 'codemirror/addon/display/placeholder';
import 'codemirror/addon/edit/continuelist';
import 'codemirror/addon/edit/matchbrackets';
import 'codemirror/addon/lint/json-lint';
import 'codemirror/addon/lint/lint';
import 'codemirror/addon/mode/overlay';
import 'codemirror/addon/mode/simple';
import 'codemirror/addon/selection/mark-selection';
import 'codemirror/mode/coffeescript/coffeescript';
import 'codemirror/mode/css/css';
import 'codemirror/mode/gfm/gfm';
import 'codemirror/mode/go/go';
import 'codemirror/mode/htmlmixed/htmlmixed';
import 'codemirror/mode/javascript/javascript';
import 'codemirror/mode/jsx/jsx';
import 'codemirror/mode/markdown/markdown';
import 'codemirror/mode/perl/perl';
import 'codemirror/mode/php/php';
import 'codemirror/mode/python/python';
import 'codemirror/mode/rst/rst';
import 'codemirror/mode/ruby/ruby';
import 'codemirror/mode/rust/rust';
import 'codemirror/mode/shell/shell';
import 'codemirror/mode/sql/sql';
import 'codemirror/mode/swift/swift';
import 'codemirror/mode/xml/xml';
import 'codemirror/mode/yaml/yaml';

/* Load our Spina/Backbone/etc. infrastructure */
import _ from 'underscore';
import Backbone from 'backbone';
import Spina from '@beanbag/spina';


/* Export what's needed to the global namespace. */
const _global = typeof globalThis !== 'undefined' ? globalThis : self;

_global.Backbone = Backbone;
_global.CodeMirror = CodeMirror;
_global.Spina = Spina;
_global._ = _;
_global.moment = moment;

/* This module doesn't import correctly, so we help it out. */
setupJQueryForm(_global, $);
