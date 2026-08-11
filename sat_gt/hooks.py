app_name = "sat_gt"
app_title = "Sat_gt"
app_publisher = "Rodrigo Castañeda"
app_description = "Applicación para importar, cuadrar y evaluar erpnext contra reportes de Sat Guatemala"
app_email = "rodrishishi@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "sat_gt",
# 		"logo": "/assets/sat_gt/logo.png",
# 		"title": "Sat_gt",
# 		"route": "/sat_gt",
# 		"has_permission": "sat_gt.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/sat_gt/css/sat_gt.css"
# app_include_js = "/assets/sat_gt/js/sat_gt.js"

# include js, css files in header of web template
# web_include_css = "/assets/sat_gt/css/sat_gt.css"
# web_include_js = "/assets/sat_gt/js/sat_gt.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "sat_gt/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "sat_gt/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "sat_gt.utils.jinja_methods",
# 	"filters": "sat_gt.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "sat_gt.install.before_install"
# after_install = "sat_gt.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "sat_gt.uninstall.before_uninstall"
# after_uninstall = "sat_gt.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "sat_gt.utils.before_app_install"
# after_app_install = "sat_gt.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "sat_gt.utils.before_app_uninstall"
# after_app_uninstall = "sat_gt.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "sat_gt.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "sat_gt.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"sat_gt.tasks.all"
# 	],
# 	"daily": [
# 		"sat_gt.tasks.daily"
# 	],
# 	"hourly": [
# 		"sat_gt.tasks.hourly"
# 	],
# 	"weekly": [
# 		"sat_gt.tasks.weekly"
# 	],
# 	"monthly": [
# 		"sat_gt.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "sat_gt.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "sat_gt.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "sat_gt.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "sat_gt.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["sat_gt.utils.before_request"]
# after_request = ["sat_gt.utils.after_request"]

# Job Events
# ----------
# before_job = ["sat_gt.utils.before_job"]
# after_job = ["sat_gt.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"sat_gt.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

