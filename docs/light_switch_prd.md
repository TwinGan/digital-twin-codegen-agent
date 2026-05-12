# Light Switch System - PRD

## Overview
A simple light switch system. A light can be turned on and off.

## Entities

### Light
- **Properties**: id (string), state (string)
- **States**: off, on

## Commands

### turn_on
Turn the light on.
- **Parameters**: light_id (string, required)
- **Behavior**: Sets light state to "on", fires event `light_turned_on`
- **Validation**: light must exist, must not already be on

### turn_off
Turn the light off.
- **Parameters**: light_id (string, required)
- **Behavior**: Sets light state to "off", fires event `light_turned_off`
- **Validation**: light must exist, must not already be off

## Business Rules
- A light that is on cannot be turned on again (idempotent safety)
- A light that is off cannot be turned off again
- Light IDs must be unique

## Scenarios

### Turn on a light
1. turn_on "kitchen" -> state=on, event=light_turned_on

### Turn off a light
1. turn_on "kitchen" -> state=on
2. turn_off "kitchen" -> state=off, event=light_turned_off

### Error: turn on an already on light
1. turn_on "kitchen" -> state=on
2. turn_on "kitchen" -> error=already_on
