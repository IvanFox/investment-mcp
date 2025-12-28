/// <reference types="@raycast/api">

/* 🚧 🚧 🚧
 * This file is auto-generated from the extension's manifest.
 * Do not modify manually. Instead, update the `package.json` file.
 * 🚧 🚧 🚧 */

/* eslint-disable @typescript-eslint/ban-types */

type ExtensionPreferences = {
  /** Project Root Path - Absolute path to investment-mcp project directory */
  "projectRootPath": string
}

/** Preferences accessible in all the extension's commands */
declare type Preferences = ExtensionPreferences

declare namespace Preferences {
  /** Preferences accessible in the `portfolio-status` command */
  export type PortfolioStatus = ExtensionPreferences & {}
  /** Preferences accessible in the `upcoming-events` command */
  export type UpcomingEvents = ExtensionPreferences & {}
}

declare namespace Arguments {
  /** Arguments passed to the `portfolio-status` command */
  export type PortfolioStatus = {}
  /** Arguments passed to the `upcoming-events` command */
  export type UpcomingEvents = {}
}

