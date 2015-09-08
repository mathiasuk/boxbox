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

import os
import sys
import traceback

import ac
# import acsys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'DLLs'))
from sim_info import info


APP_SIZE_X = 300
APP_SIZE_Y = 200
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
        ac.addRenderCallback(self.widget, onFormRender)

    def _create_label(self, name, text, x, y):
        label = ac.addLabel(self.widget, name)
        ac.setText(label, text)
        ac.setPosition(label, x, y)
        self.labels[name] = label

    def _create_labels(self):
        self._create_label('current_lap_title', 'Current lap', 10, 30)
        self._create_label('current_lap', '', 100, 30)
        self._create_label('laps_title', 'Laps', 10, 50)
        self._create_label('laps', '', 100, 50)
        self._create_label('fuel_title', 'Fuel', 10, 70)
        self._create_label('fuel', '', 100, 70)
        self._create_label('consumption_title', 'Consumption', 10, 90)
        self._create_label('consumption', '', 100, 90)
        self._create_label('left_title', 'Laps to empty', 10, 110)
        self._create_label('left', '', 100, 110)


class Session(object):
    '''
    Represent a racing sessions.
    '''
    def __init__(self):
        self.ui = None
        self.current_lap = 0
        self.laps = 0
        self.initial_fuel = 0
        self.fuel = 0
        self.consumption = 0  # in litres per lap
        self.spline_pos = 0
        self.laps_since_pit = 0
        self.laps_left = 0

    def _set_distance(self):
        current_lap = info.graphics.completedLaps
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

        if fuel > self.fuel:
            # Car was refuelled
            self.initial_fuel = fuel
            self.laps_since_pit = 0
        else:
            distance = self.laps_since_pit + self.spline_pos
            ac.console('* %.2f %d %.2f %.2f' % (distance, self.current_lap, self.initial_fuel, self.fuel))
            self.consumption = (self.initial_fuel - self.fuel) / distance
            if self.consumption != 0:
                self.laps_left = self.fuel / self.consumption

        self.fuel = fuel

    def render(self):
        label = self.ui.labels['current_lap']
        ac.setFontColor(label, *WHITE)
        ac.setText(label, '%d' % self.current_lap)
        label = self.ui.labels['laps']
        ac.setFontColor(label, *WHITE)
        ac.setText(label, '%d' % self.laps)
        label = self.ui.labels['fuel']
        ac.setFontColor(label, *WHITE)
        ac.setText(label, '%.2f' % self.fuel)
        label = self.ui.labels['consumption']
        ac.setFontColor(label, *WHITE)
        ac.setText(label, '%.2f' % self.consumption)
        label = self.ui.labels['left']
        ac.setFontColor(label, *WHITE)
        ac.setText(label, '%.2f' % self.laps_left)

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


def onFormRender(deltaT):
    global session  # pylint: disable=W0602

    try:
        session.render()
    except:  # pylint: disable=W0702
        exc_type, exc_value, exc_traceback = sys.exc_info()
        ac.console('ACTracker Error (logged to file)')
        ac.log(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))
