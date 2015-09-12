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

import math
import os
import sys
import traceback

import ac
# import acsys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'DLLs'))
from sim_info import info

N_LAPS_DISPLAY = 1.5
LITRES_MARGIN = 2

APP_SIZE_X = 300
APP_SIZE_Y = 200

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

        self._create_widget()
        self._create_labels()

    def _create_widget(self):
        self.widget = ac.newApp('Box box!')
        ac.setSize(self.widget, APP_SIZE_X, APP_SIZE_Y)
        # ac.setBackgroundOpacity(self.widget, 0)
        ac.addRenderCallback(self.widget, form_render_callback)

    def _create_label(self, name, text, x, y):
        label = ac.addLabel(self.widget, name)
        ac.setText(label, text)
        ac.setPosition(label, x, y)
        self.labels[name] = label

    def _create_labels(self):
        self._create_label('message1', '', 10, 30)
        self._create_label('message2', '', 10, 50)


class Session(object):
    '''
    Represent a racing sessions.
    '''
    def __init__(self):
        self.ui = None
        self.current_lap = 0
        self.laps = 0
        self.initial_fuel = -1
        self.fuel = 0
        self.consumption = 0  # in litres per lap
        self.spline_pos = 0
        self.laps_since_pit = 0
        self.laps_left = 0
        self.litres = -1

    def _set_distance(self):
        current_lap = info.graphics.completedLaps + 1  # 0 indexed
        self.spline_pos = info.graphics.normalizedCarPosition

        if current_lap > self.current_lap:
            self.laps_since_pit += 1
            # TODO: handle teleportation

        self.current_lap = current_lap

    def _set_fuel(self):
        '''
        Set the current fuel, calculate the consumption
        '''
        fuel = info.physics.fuel

        if self.initial_fuel == -1 and not info.physics.pitLimiterOn:
			# Beginning of the session, check the initial fuel after
			# exiting the pit or on the grid
            self.initial_fuel = fuel
        elif fuel > self.fuel:
            # Car was refuelled
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
            litres = (self.laps - self.current_lap) * self.consumption

            self.litres = math.ceil(litres) + LITRES_MARGIN
            # ac.console('* Conso:%.2f fuel:%.2f dist:%.1f litres:%d' % (self.consumption, self.fuel, distance, self.litres))
            # ac.console('* Init fuel: %.1f laps: %d, pos: %.1f' % (self.initial_fuel, self.laps_since_pit, self.spline_pos))

        self.fuel = fuel

    def render(self):
        label = self.ui.labels['message1']
        ac.setFontColor(label, *WHITE)
        ac.setText(label, 'Left: %.1f, Conso: %.1f, Current lap: %d' % (self.laps_left, self.consumption, self.current_lap))

        label = self.ui.labels['message2']
        if self.laps_left < N_LAPS_DISPLAY and self.laps_since_pit > 1:
            ac.setFontColor(label, *RED)
            ac.setText(label, 'Box Box Box! %dl to finish race' % self.litres)
        else:
            ac.setText(label, '')

    def update_data(self):
        self.laps = info.graphics.numberOfLaps

        self._set_distance()
        self._set_fuel()


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
    except:  # pylint: disable=W0702
        exc_type, exc_value, exc_traceback = sys.exc_info()
        ac.console('ACTracker Error (logged to file)')
        ac.log(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))


def form_render_callback(deltaT):
    global session  # pylint: disable=W0602

    try:
        session.render()
    except:  # pylint: disable=W0702
        exc_type, exc_value, exc_traceback = sys.exc_info()
        ac.console('ACTracker Error (logged to file)')
        ac.log(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
