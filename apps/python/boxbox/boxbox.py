# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# Copyright (C) 2014 - Mathias Andre

import json
import os
import platform
import sys
import traceback
from datetime import datetime

import ac

sys.path.insert(
    0, 'apps/python/boxbox/boxboxDLL/%s/' % platform.architecture()[0]
)

from boxboxDLL.sim_info import info

N_LAPS_DISPLAY = 1.3
FUEL_MARGIN = 3

APP_SIZE_X = 300
APP_SIZE_Y = 70
PREFS_PATH = 'apps/python/boxbox/prefs.json'
DISPLAY = True
TITLE_TIMEOUT = 10  # Time in seconds during which we show the title

GREEN = (0, 1, 0, 1)
RED = (1, 0, 0, 1)
WHITE = (1, 1, 1, 1)

session = None


class UI(object):
    '''
    Object that deals with everything related to the app's widget
    '''
    def __init__(self, session_):
        self.session = session_
        self.widget = None
        self.labels = {}
        self.display_button = None
        self.display_title_start = None

        self._create_widget()
        self._create_labels()
        self.activated()

    def _create_widget(self):
        self.widget = ac.newApp('boxbox')
        ac.setSize(self.widget, APP_SIZE_X, APP_SIZE_Y)
        # ac.addOnAppActivatedListener(self.widget, app_activated_callback)
        ac.setIconPosition(self.widget, -10000, -10000)
        ac.drawBorder(self.widget, 0)
        self.hide_bg()

        # Create display button
        self.display_button = ac.addButton(self.widget, '')
        ac.setPosition(self.display_button, 0, 30)
        ac.setSize(self.display_button, 300, 60)
        ac.setBackgroundOpacity(self.display_button, 0)
        ac.drawBorder(self.display_button, 0)
        ac.addOnClickedListener(self.display_button, callback_display_button)

        ac.addOnAppActivatedListener(self.widget, activated_callback)

    def _create_label(self, name, text, x, y):
        label = ac.addLabel(self.widget, name)
        ac.setText(label, text)
        ac.setPosition(label, x, y)
        self.labels[name] = label

    def _create_labels(self):
        self._create_label('message1', '', 10, 30)

    def activated(self):
        '''
        Called at start or when the app is (re)activated
        '''
        self.display_title_start = datetime.now()

    def display_button_click(self):
        self.session.display = not self.session.display

        # Save preferences
        self.session.save_prefs()

    def hide_bg(self):
        ac.setBackgroundOpacity(self.widget, 0)

    def set_bg_color(self, color):
        ac.setBackgroundColor(self.widget, *color[:-1])

    def set_title(self, text):
        ac.setTitle(self.widget, text)

    def show_bg(self):
        ac.setBackgroundOpacity(self.widget, 0.7)


class Session(object):
    '''
    Represent a racing sessions.
    '''
    def __init__(self):
        self.ui = None
        self.display = DISPLAY
        self._reset()

        self._load_prefs()

    def _is_race(self):
        '''
        Return true if the current session is a race
        '''
        return info.graphics.session == 2  # Only run in race mode

    def _load_prefs(self):
        if not os.path.exists(PREFS_PATH):
            return

        try:
            f = open(PREFS_PATH)
        except Exception as e:
            ac.console('Pitboard: Error opining "%s": %s' % (PREFS_PATH, e))
            return

        data = f.readline()
        data = json.loads(data)
        if 'display' in data:
            self.display = data['display']

    def _reset(self):
        self.current_lap = 0
        self.laps = 0
        self.initial_fuel = -1
        self.fuel = 0
        self.consumption = 0  # in litres per lap
        self.spline_pos = 0
        self.in_pits = False
        self.laps_since_pit = 0
        self.current_lap_time = 0
        self.laps_left = 0
        self.fuel_needed = -1
        self.activated = None

    def _set_distance(self):
        current_lap = info.graphics.completedLaps + 1  # 0 indexed
        self.spline_pos = info.graphics.normalizedCarPosition
        self.current_lap_time = info.graphics.iCurrentTime

        if current_lap > self.current_lap:
            self.laps_since_pit += 1
            # TODO: handle teleportation
        elif current_lap < self.current_lap:
            # Must be a session reset or next session starting
            self._reset()

        self.current_lap = current_lap

    def _set_fuel(self):
        '''
        Set the current fuel, calculate the consumption
        '''
        fuel = info.physics.fuel

        if self.initial_fuel == -1:
			# Beginning of the session, check the initial fuel after
			# exiting the pit or on the grid
            self.initial_fuel = fuel
        elif abs(self.fuel - fuel) > 0.5:
            # Car was refuelled (only case were fuel would change
            # by 0.5l within two updates)
            self.initial_fuel = fuel
            self.laps_since_pit = 0
        else:
            distance = self.laps_since_pit + self.spline_pos
            if distance != 0:
                self.consumption = (self.initial_fuel - self.fuel) / distance

            if self.consumption != 0:
                self.laps_left = self.fuel / self.consumption

            # Calculate the amount of fuel needed from end of lap till
            # end of the race
            fuel_needed = (self.laps - self.current_lap) * self.consumption

            if not self.in_pits:
                # Only update the amount of fuel needed if not in the pits
                ceiling = int(fuel_needed)
                ceiling = ceiling + 1 if ceiling < fuel_needed else ceiling
                self.fuel_needed = ceiling + FUEL_MARGIN
            # ac.console('* Conso:%.2f fuel:%.2f dist:%.1f fuel_needed:%d' % (self.consumption, self.fuel, distance, self.fuel_needed))
            # ac.console('* Init fuel: %.1f laps-since: %d, lap: %d/%d, pos: %.1f, left: %.1f' % (self.initial_fuel, self.laps_since_pit, self.current_lap, self.laps, self.spline_pos, self.laps_left))

        self.fuel = fuel

    def _set_pit(self):
        '''
        Check if we are in the pits
        '''
        if info.physics.pitLimiterOn or info.graphics.isInPit:
            self.in_pits = True
        elif info.physics.speedKmh > 81:
            self.in_pits = False

    def update_ui(self):
        label = self.ui.labels['message1']

        display_time = (datetime.now() -
                        self.ui.display_title_start).total_seconds()

        if self.display or display_time < TITLE_TIMEOUT:
            # Show fuel left in title
            self.ui.set_title('boxbox (%.1fl)' % info.physics.fuel)
        else:
            self.ui.set_title('')

        if not self._is_race():
            ac.setText(label, '')
            self.ui.hide_bg()
            return

        if self.laps_left < N_LAPS_DISPLAY and \
                not (self.current_lap == 1 and self.current_lap_time < 30 * 1000) and \
                self.laps_left < self.laps - (self.current_lap + self.spline_pos):
            # Car has less thatn N_LAPS_DISPLAY of fuel left in tank, indicate
            # that the players has to pit ASAP
            # We do not display in the first 30 seconds of lap 1 while we
            # calculate the initial fuel consumption
            # We also do not display if we have enough fuel to finish the race
            self.ui.set_bg_color(RED)
            self.ui.show_bg()
            ac.setFontColor(label, *WHITE)
            ac.setText(label, 'Box Box Box! Needs %d l to finish the race' %
                       self.fuel_needed)
        elif self.in_pits and self.fuel < self.fuel_needed:
            # Player is in the pits before necessary and needs to refuel to
            # finish the race without pitting again
            self.ui.set_bg_color(RED)
            self.ui.show_bg()
            ac.setFontColor(label, *WHITE)
            ac.setText(label, 'Early pit! Needs %d l to finish the race' %
                       self.fuel_needed)
        elif self.in_pits and self.fuel >= self.fuel_needed:
            # Player is in the pits before necessary and has enough fuel to
            # finish the race without refueling
            self.ui.set_bg_color(GREEN)
            self.ui.show_bg()
            ac.setFontColor(label, *WHITE)
            ac.setText(label, 'Enough fuel to finish the race: %d l' %
                       self.fuel)
        else:
            ac.setText(label, '')
            self.ui.hide_bg()

    def update_data(self):
        if self._is_race():
            self.laps = info.graphics.numberOfLaps

            self._set_pit()
            self._set_distance()
            self._set_fuel()

    def save_prefs(self):
        '''
        Save preferences to JSON file
        '''
        try:
            f = open(PREFS_PATH, 'w')
        except Exception as e:
            ac.console('Can\'t open file "%s" for writing: %s' %
                       (PREFS_PATH, e))
            return

        f.write(json.dumps({'display': self.display}))
        f.close()
        ac.console('Wrote prefs to file')


def acMain(ac_version):
    global session  # pylint: disable=W0603

    # Create session object
    session = Session()

    # Initialise UI:
    ui = UI(session)
    session.ui = ui

    return "Box box!"


def acUpdate(deltaT):
    global session  # pylint: disable=W0602

    try:
        session.update_data()
        session.update_ui()
    except:  # pylint: disable=W0702
        exc_type, exc_value, exc_traceback = sys.exc_info()
        ac.console('boxbox Error (logged to file)')
        ac.log(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))


def callback_display_button(x, y):
    global session  # pylint: disable=W0602

    session.ui.display_button_click()


def activated_callback(value):
    global session  # pylint: disable=W0602
    session.ui.activated()
