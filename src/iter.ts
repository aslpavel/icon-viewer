export class Iter<T> {
    iter: Iterator<T>;

    constructor(iterable: Iterable<T>) {
        this.iter = iterable[Symbol.iterator]();
    }

    [Symbol.iterator](): Iterator<T> {
        return this.iter;
    }

    next(): IteratorResult<T> {
        return this.iter.next();
    }

    static from<T>(iter: Iterable<T>): Iter<T> {
        return new Iter(iter);
    }

    static range(start: number, stop?: number, step: number = 1): Iter<number> {
        function* rangeGen() {
            if (stop === undefined) {
                stop = start;
                start = 0;
            }
            for (let i = start; step > 0 ? i < stop : i > stop; i += step) {
                yield i;
            }
        }
        return new Iter(rangeGen());
    }

    static zip<Iters extends any[]>(...iterables: Iters): Iter<ZipItem<Iters>> {
        const iters = iterables.map((iter) => iter[Symbol.iterator]());
        const iterCount = iterables.length;
        function* zipGen() {
            while (true) {
                let item = [];
                for (let iterIndex = 0; iterIndex < iterCount; iterIndex++) {
                    const iterResult = iters[iterIndex]!.next();
                    if (iterResult.done) {
                        return;
                    }
                    item.push(iterResult.value);
                }
                yield item as ZipItem<Iters>;
            }
        }
        return new Iter(zipGen());
    }

    zip<O>(other: Iterable<O>): Iter<readonly [T, O]> {
        return this.applyGenFn(function* zipGen(iter) {
            const thisIter = iter[Symbol.iterator]();
            const otherIter = other[Symbol.iterator]();
            while (true) {
                let thisItem = thisIter.next();
                let otherItem = otherIter.next();
                if (thisItem.done || otherItem.done) {
                    return;
                }
                yield [thisItem.value, otherItem.value] as const;
            }
        });
    }

    enumerate(): Iter<readonly [number, T]> {
        return this.applyGenFn(function* enumerateGen(iter) {
            let index = 0;
            for (let item of iter) {
                yield [index, item];
                index += 1;
            }
        });
    }

    map<O>(mapFn: (item: T) => O): Iter<O> {
        return this.applyGenFn(function* mapGen(iter) {
            for (let item of iter) {
                yield mapFn(item);
            }
        });
    }

    filter(predFn: (item: T) => boolean): Iter<T> {
        return this.applyGenFn(function* filterGen(iter) {
            for (let item of iter) {
                if (predFn(item)) {
                    yield item;
                }
            }
        });
    }

    filterMap<O>(filterMapFn: (item: T) => O): Iter<NonNullable<O>> {
        return this.applyGenFn(function* filterMapGen(iter) {
            for (let outerItem of iter) {
                const innerItem = filterMapFn(outerItem);
                if (innerItem) {
                    yield innerItem;
                }
            }
        });
    }

    flatMap<O>(flatMapFn: (item: T) => Iterable<O>): Iter<O> {
        return this.applyGenFn(function* flatMapGen(iter) {
            for (let outerItem of iter) {
                let innerItems = flatMapFn(outerItem);
                if (innerItems) {
                    for (let innerItem of innerItems) {
                        yield innerItem;
                    }
                }
            }
        });
    }

    forEach(forEachFn: (item: T) => void): void {
        for (let item of this) {
            forEachFn(item);
        }
    }

    fold<O>(initialValue: O, foldFn: (acc: O, item: T) => O): O {
        let acc = initialValue;
        for (let item of this) {
            acc = foldFn(acc, item);
        }
        return acc;
    }

    collectArray(array: Array<T> | undefined = undefined): Array<T> {
        array = array === undefined ? new Array() : array;
        for (const item of this) {
            array.push(item);
        }
        return array;
    }

    collectSet(set: Set<T> | undefined = undefined): Set<T> {
        set = set === undefined ? new Set() : set;
        for (const item of this) {
            set.add(item);
        }
        return set;
    }

    collectMap<K, V>(
        this: Iter<readonly [K, V]>,
        map: Map<K, V> | undefined = undefined
    ): Map<K, V> {
        map = map === undefined ? new Map() : map;
        for (const [key, value] of this) {
            map.set(key, value);
        }
        return map;
    }

    collectObject<V>(this: Iter<readonly [PropertyKey, V]>): {
        [k: string]: V;
    } {
        return Object.fromEntries(this);
    }

    private applyGenFn<O>(genFn: (iter: Iterable<T>) => Iterable<O>): Iter<O> {
        return new Iter(genFn(this));
    }
}

type ZipItem<Iters extends unknown[]> = {
    readonly [K in keyof Iters]: Iters[K] extends Iterable<infer V> ? V : never;
};
