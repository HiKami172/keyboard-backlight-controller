"""MainWindow — GTK4/libadwaita configuration window for keyboard backlight control.

Provides mode selector (ComboRow), color picker (ColorDialogButton), speed buttons
(linked ToggleButton group), and profile load/save/delete UI. All hardware changes
use a 100ms debounced live preview (persist=False). Only explicit profile saves and
loads write persist=True to firmware.

Closing the window hides it rather than destroying it — preparing for the Phase 4
tray icon which will re-show it via Application.show_window().
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, GLib

from kbd_backlight.hardware.backlight import BacklightController
from kbd_backlight.profiles.manager import ProfileManager
from kbd_backlight.profiles.profile import Profile


MODE_NAMES = ['Static', 'Breathing', 'Color Cycle', 'Strobe']
MODE_KEYS  = ['static', 'breathing', 'color_cycle', 'strobe']

PRESETS = [
    ('Ocean',       0,   100, 255),
    ('Sunset',    255,    80,  20),
    ('Cyberpunk',   0,   255, 180),
    ('Crimson',   200,     0,  50),
    ('Gold',      255,   180,   0),
    ('Lilac',     160,    80, 220),
    ('Glacier',   100,   220, 255),
    ('Monochrome',220,   220, 220),
]


class MainWindow(Adw.ApplicationWindow):
    """Full-featured keyboard backlight configuration window.

    Parameters
    ----------
    controller:
        BacklightController instance owned by Application.
    manager:
        ProfileManager instance owned by Application.
    **kwargs:
        Passed through to Adw.ApplicationWindow (e.g. application=app).
    """

    def __init__(self, controller: BacklightController, manager: ProfileManager, **kwargs):
        super().__init__(**kwargs)
        self._controller = controller
        self._manager = manager
        self._debounce_id: int | None = None
        self._loading = False  # Guard against notify::rgba firing during profile load

        self.set_title('Keyboard Backlight')
        self.set_default_size(480, 640)

        # Window structure: ToastOverlay > ToolbarView > ScrolledWindow > content
        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        scroll.set_child(content_box)
        toolbar_view.set_content(scroll)

        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(toolbar_view)
        self.set_content(self._toast_overlay)

        self._build_backlight_controls(content_box)
        self._build_profile_section(content_box)
        self._build_palette(content_box)

    def do_close_request(self):
        """Hide window on close instead of quitting (TRAY-05 prep for Phase 4)."""
        self.hide()
        return True  # Suppress default close/destroy

    # ── Backlight controls ─────────────────────────────────────────────────

    def _build_backlight_controls(self, parent: Gtk.Box):
        group = Adw.PreferencesGroup()
        group.set_title('Backlight')

        # Mode selector (Adw.ComboRow)
        self._mode_row = Adw.ComboRow()
        self._mode_row.set_title('Mode')
        self._mode_row.set_model(Gtk.StringList.new(MODE_NAMES))
        self._mode_row.set_expression(
            Gtk.PropertyExpression.new(Gtk.StringObject, None, 'string')
        )
        self._mode_row.connect('notify::selected', self._on_mode_changed)
        group.add(self._mode_row)

        # Color picker (Gtk.ColorDialogButton — NOT deprecated ColorButton)
        color_row = Adw.ActionRow()
        color_row.set_title('Color')
        color_dialog = Gtk.ColorDialog.new()
        color_dialog.set_title('Pick keyboard color')
        color_dialog.set_with_alpha(False)
        self._color_button = Gtk.ColorDialogButton.new(color_dialog)
        self._color_button.set_valign(Gtk.Align.CENTER)
        # Default: white (255, 255, 255)
        default_rgba = Gdk.RGBA()
        default_rgba.red = default_rgba.green = default_rgba.blue = 1.0
        default_rgba.alpha = 1.0
        self._color_button.set_rgba(default_rgba)
        self._color_button.connect('notify::rgba', self._on_color_changed)
        color_row.add_suffix(self._color_button)
        group.add(color_row)

        # Speed selector (Gtk.ToggleButton group with 'linked' CSS class)
        speed_row = Adw.ActionRow()
        speed_row.set_title('Speed')
        speed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        speed_box.add_css_class('linked')
        speed_box.set_valign(Gtk.Align.CENTER)
        self._btn_slow   = Gtk.ToggleButton(label='Slow')
        self._btn_medium = Gtk.ToggleButton(label='Medium')
        self._btn_fast   = Gtk.ToggleButton(label='Fast')
        self._btn_medium.set_group(self._btn_slow)
        self._btn_fast.set_group(self._btn_slow)
        self._btn_slow.set_active(True)  # default: slow
        for btn in (self._btn_slow, self._btn_medium, self._btn_fast):
            btn.connect('toggled', self._on_speed_changed)
            speed_box.append(btn)
        speed_row.add_suffix(speed_box)
        self._speed_row = speed_row
        group.add(speed_row)

        parent.append(group)

    def _on_mode_changed(self, row, _pspec):
        # Update speed row sensitivity: speed is irrelevant for Static mode
        is_static = MODE_KEYS[row.get_selected()] == 'static'
        self._speed_row.set_sensitive(not is_static)
        self._schedule_preview()

    def _on_color_changed(self, _button, _pspec):
        self._schedule_preview()

    def _on_speed_changed(self, button):
        if button.get_active():  # Guard: fires twice (deactivated + activated)
            self._schedule_preview()

    # ── Debounced live preview ─────────────────────────────────────────────

    def _schedule_preview(self):
        """Cancel any pending preview and schedule one 100ms from now."""
        if self._loading:
            return
        if self._debounce_id is not None:
            GLib.source_remove(self._debounce_id)
        self._debounce_id = GLib.timeout_add(100, self._apply_preview)

    def _apply_preview(self):
        """Called ~100ms after last control change. Writes to hardware with persist=False."""
        self._debounce_id = None
        r, g, b = self._get_rgb()
        try:
            self._controller.apply(
                mode=self._current_mode(),
                r=r, g=g, b=b,
                speed=self._current_speed(),
                persist=False,  # cmd=0 — NEVER persist during live preview
            )
        except Exception:
            pass  # Don't crash window on hardware error during preview
        return GLib.SOURCE_REMOVE  # Critical: run exactly once

    def _current_mode(self) -> str:
        return MODE_KEYS[self._mode_row.get_selected()]

    def _current_speed(self) -> int:
        for i, btn in enumerate([self._btn_slow, self._btn_medium, self._btn_fast]):
            if btn.get_active():
                return i
        return 0

    def _get_rgb(self) -> tuple[int, int, int]:
        rgba = self._color_button.get_rgba()
        # Use round() not int() — int(128/255*255) truncates to 127 due to float precision
        return (
            round(rgba.red   * 255),
            round(rgba.green * 255),
            round(rgba.blue  * 255),
        )

    # ── Profile section ────────────────────────────────────────────────────

    def _build_profile_section(self, parent: Gtk.Box):
        group = Adw.PreferencesGroup()
        group.set_title('Profiles')

        # Profile dropdown
        self._profile_row = Adw.ComboRow()
        self._profile_row.set_title('Active Profile')
        self._refresh_profile_list()
        self._profile_row.connect('notify::selected', self._on_profile_selected)
        group.add(self._profile_row)

        # Save button row
        save_row = Adw.ActionRow()
        save_row.set_title('Save Profile')
        save_row.set_subtitle('Save current settings as a named profile')
        save_btn = Gtk.Button(label='Save…')
        save_btn.add_css_class('suggested-action')
        save_btn.set_valign(Gtk.Align.CENTER)
        save_btn.connect('clicked', self._on_save_clicked)
        save_row.add_suffix(save_btn)
        group.add(save_row)

        # Delete button row
        delete_row = Adw.ActionRow()
        delete_row.set_title('Delete Profile')
        delete_row.set_subtitle('Remove the selected profile')
        delete_btn = Gtk.Button(label='Delete')
        delete_btn.add_css_class('destructive-action')
        delete_btn.set_valign(Gtk.Align.CENTER)
        delete_btn.connect('clicked', self._on_delete_clicked)
        delete_row.add_suffix(delete_btn)
        group.add(delete_row)

        parent.append(group)

    def _refresh_profile_list(self):
        names = self._manager.list_profiles()
        model = Gtk.StringList.new(names if names else ['(no profiles)'])
        self._profile_row.set_model(model)

    def _on_profile_selected(self, row, _pspec):
        idx = row.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION:
            return
        names = self._manager.list_profiles()
        if not names or idx >= len(names):
            return
        profile = self._manager.get_profile(names[idx])
        if profile is None:
            return
        self._load_profile_into_controls(profile)
        try:
            self._controller.apply(
                profile.mode, profile.r, profile.g, profile.b,
                profile.speed, persist=True,  # cmd=1 — explicit profile load persists
            )
        except Exception:
            pass
        self._manager.set_last_profile(profile.name)

    def _load_profile_into_controls(self, profile: Profile):
        """Load profile values into UI controls. Sets _loading=True to suppress debounce."""
        self._loading = True
        try:
            # Mode
            key = profile.mode
            idx = MODE_KEYS.index(key) if key in MODE_KEYS else 0
            self._mode_row.set_selected(idx)
            # Color — use round() on the inverse conversion for precision
            rgba = Gdk.RGBA()
            rgba.red   = profile.r / 255.0
            rgba.green = profile.g / 255.0
            rgba.blue  = profile.b / 255.0
            rgba.alpha = 1.0
            self._color_button.set_rgba(rgba)
            # Speed
            [self._btn_slow, self._btn_medium, self._btn_fast][profile.speed].set_active(True)
        finally:
            self._loading = False

    def _on_save_clicked(self, _btn):
        self._show_save_dialog()

    def _show_save_dialog(self):
        """Show Adw.Dialog with EntryRow for profile name input."""
        dialog = Adw.Dialog.new()
        dialog.set_title('Save Profile')
        dialog.set_content_width(360)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        entry = Adw.EntryRow.new()
        entry.set_title('Profile Name')
        box.append(entry)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_halign(Gtk.Align.END)
        cancel_btn = Gtk.Button(label='Cancel')
        save_btn   = Gtk.Button(label='Save')
        save_btn.add_css_class('suggested-action')
        cancel_btn.connect('clicked', lambda _: dialog.close())
        save_btn.connect('clicked', lambda _: self._do_save(entry.get_text(), dialog))
        button_box.append(cancel_btn)
        button_box.append(save_btn)
        box.append(button_box)

        dialog.set_child(box)
        dialog.present(self)

    def _do_save(self, name: str, dialog):
        name = name.strip()
        if not name:
            return
        r, g, b = self._get_rgb()
        profile = Profile(
            name=name,
            mode=self._current_mode(),
            r=r, g=g, b=b,
            speed=self._current_speed(),
        )
        self._manager.save_profile(profile)
        self._manager.set_last_profile(name)
        self._refresh_profile_list()
        try:
            self._controller.apply(
                profile.mode, profile.r, profile.g, profile.b,
                profile.speed, persist=True,  # cmd=1 — explicit save persists to BIOS
            )
        except Exception:
            pass
        self._toast_overlay.add_toast(Adw.Toast.new(f'Profile "{name}" saved'))
        dialog.close()

    def _on_delete_clicked(self, _btn):
        idx = self._profile_row.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION:
            return
        names = self._manager.list_profiles()
        if not names or idx >= len(names):
            return
        profile_name = names[idx]
        self._confirm_delete(profile_name)

    def _confirm_delete(self, profile_name: str):
        """Show Adw.AlertDialog for delete confirmation."""
        dialog = Adw.AlertDialog.new(
            f'Delete "{profile_name}"?',
            'This profile will be permanently removed.',
        )
        dialog.add_response('cancel', 'Cancel')
        dialog.add_response('delete', 'Delete')
        dialog.set_response_appearance('delete', Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response('cancel')
        dialog.set_close_response('cancel')
        dialog.connect('response', self._on_delete_response, profile_name)
        dialog.present(self)

    def _on_delete_response(self, _dialog, response, profile_name):
        if response == 'delete':
            self._manager.delete_profile(profile_name)
            self._refresh_profile_list()
            self._toast_overlay.add_toast(Adw.Toast.new(f'Deleted "{profile_name}"'))

    # ── Color palette presets ──────────────────────────────────────────────

    def _build_palette(self, parent: Gtk.Box):
        group = Adw.PreferencesGroup()
        group.set_title('Color Presets')

        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(4)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_margin_top(8)
        flow.set_margin_bottom(8)
        flow.set_margin_start(8)
        flow.set_margin_end(8)
        flow.set_row_spacing(8)
        flow.set_column_spacing(8)

        for name, r, g, b in PRESETS:
            btn = Gtk.Button()
            btn.set_tooltip_text(name)
            btn.set_size_request(48, 48)
            btn.add_css_class('circular')

            rgba = Gdk.RGBA()
            rgba.red, rgba.green, rgba.blue, rgba.alpha = r / 255, g / 255, b / 255, 1.0
            css = f'button {{ background-color: {rgba.to_string()}; }}'
            provider = Gtk.CssProvider()
            provider.load_from_string(css)
            btn.get_style_context().add_provider(
                provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

            btn.connect('clicked', self._on_preset_clicked, r, g, b)
            flow.append(btn)

        group.add(flow)
        parent.append(group)

    def _on_preset_clicked(self, _btn, r: int, g: int, b: int):
        """Set ColorDialogButton to preset color. notify::rgba fires -> _schedule_preview()."""
        rgba = Gdk.RGBA()
        rgba.red   = r / 255.0
        rgba.green = g / 255.0
        rgba.blue  = b / 255.0
        rgba.alpha = 1.0
        self._color_button.set_rgba(rgba)
        # notify::rgba fires automatically from set_rgba() -> _schedule_preview() called
        # No explicit _schedule_preview() needed here — would cause double debounce
