import { expect, test, describe } from "bun:test";
import { Iter } from "./iter.js";

describe("Iter", () => {
    test("zip", () => {
        const keys = [1, 2, 3];
        const vals = ["one", "two", "three"];
        const map = Iter.zip(keys, vals).collectMap(new Map([[0, "zero"]]));
        expect(map).toEqual(
            new Map([
                [0, "zero"],
                [1, "one"],
                [2, "two"],
                [3, "three"],
            ])
        );

        const mapSmall = Iter.from(keys).zip(vals).collectMap();
        expect(mapSmall).toEqual(
            new Map([
                [1, "one"],
                [2, "two"],
                [3, "three"],
            ])
        );
    });

    test("range", () => {
        let vals = Iter.range(3).collectArray();
        expect(vals).toEqual([0, 1, 2]);

        vals = Iter.range(1, 4).collectArray();
        expect(vals).toEqual([1, 2, 3]);

        vals = Iter.range(1, 10, 2).collectArray();
        expect(vals).toEqual([1, 3, 5, 7, 9]);
    });
});
